import argparse
import os
import shutil
import time

import torch
import torch.nn as nn
import torch.nn.parallel
import torch.backends.cudnn as cudnn
import torch.optim
import torch.utils.data
import torchvision.transforms as transforms
import torchvision.datasets as datasets

from torch.utils.data import DataLoader

import resnet
#import calc_normalize
import lontar_dataset.sampler as weights
from lontar_dataset.lontar_dataset import LontarDataset

model_names = sorted(name for name in resnet.__dict__
    if name.islower() and not name.startswith("__")
                     # and name.startswith("resnet")
                     and callable(resnet.__dict__[name]))

parser = argparse.ArgumentParser(description='Propert ResNets for CIFAR10 in pytorch')
parser.add_argument('--arch', '-a', metavar='ARCH', default='resnet32',
                    choices=model_names,
                    help='model architecture: ' + ' | '.join(model_names) +
                    ' (default: resnet32)')
parser.add_argument('-j', '--workers', default=4, type=int, metavar='N',
                    help='number of data loading workers (default: 4)')
parser.add_argument('--epochs', default=200, type=int, metavar='N',
                    help='number of total epochs to run')
parser.add_argument('--start-epoch', default=0, type=int, metavar='N',
                    help='manual epoch number (useful on restarts)')
parser.add_argument('-b', '--batch-size', default=128, type=int,
                    metavar='N', help='mini-batch size (default: 128)')
parser.add_argument('--lr', '--learning-rate', default=0.1, type=float,
                    metavar='LR', help='initial learning rate')
parser.add_argument('--momentum', default=0.9, type=float, metavar='M',
                    help='momentum')
parser.add_argument('--weight-decay', '--wd', default=1e-4, type=float,
                    metavar='W', help='weight decay (default: 1e-4)')
parser.add_argument('--print-freq', '-p', default=50, type=int,
                    metavar='N', help='print frequency (default: 50)')
parser.add_argument('--resume', default='', type=str, metavar='PATH',
                    help='path to latest checkpoint (default: none)')
parser.add_argument('-e', '--evaluate', dest='evaluate', action='store_true',
                    help='evaluate model on validation set')
parser.add_argument('--pretrained', dest='pretrained', action='store_true',
                    help='use pre-trained model')
parser.add_argument('--half', dest='half', action='store_true',
                    help='use half-precision(16-bit) ')
parser.add_argument('--save-dir', dest='save_dir',
                    help='The directory used to save the trained models',
                    default='save_temp', type=str)
parser.add_argument('--save-every', dest='save_every',
                    help='Saves checkpoints at every specified number of epochs',
                    type=int, default=10)
parser.add_argument('--resize', dest='resize',
                    help='Adjust resize transform (aspect ratio is always 1:1)',
                    type=int, default=32)
parser.add_argument('--grayscale', dest='grayscale', action='store_true',
                    help='Perform Grayscale pre-proc. to images')
parser.add_argument('--autocontrast', dest='autocontrast', action='store_true',
                    help='Perform AutoContrast pre-proc. to images')
parser.add_argument('--gauss', dest='gauss', action='store_true',
                    help='Perform GaussBlur pre-proc. to images (def. sigma = 1)')
parser.add_argument('--sigma', dest='sigma', action='store_true',
                    help='Set GaussianBlur sigma to 1. Requires --gauss (program will still run but will not perform GaussBlur)')

def main():
    global args, best_prec1
    args = parser.parse_args()

    data = []
    losses = []
    err1s = []
    err5s = []
    best_err1s = []
    best_err5s = []
    best_prec1 = 0
    best_prec5 = 0

    # Check the save_dir exists or not
    if not os.path.exists(args.save_dir):
        os.makedirs(args.save_dir)

    model = torch.nn.DataParallel(resnet.__dict__[args.arch]())
    model.cuda()

    # optionally resume from a checkpoint
    if args.resume:
        if os.path.isfile(args.resume):
            print("=> loading checkpoint '{}'".format(args.resume))
            checkpoint = torch.load(args.resume)
            args.start_epoch = checkpoint['epoch']
            best_prec1 = checkpoint['best_prec1']
            model.load_state_dict(checkpoint['state_dict'])
            print("=> loaded checkpoint '{}' (epoch {})"
                  .format(args.evaluate, checkpoint['epoch']))
        else:
            print("=> no checkpoint found at '{}'".format(args.resume))

    cudnn.benchmark = True

    #normalize = transforms.Normalize(mean=[0.485, 0.456, 0.406],
    #                                 std=[0.229, 0.224, 0.225])
    
    transforms_compose = [
        transforms.ToPILImage(),
        transforms.Resize([args.resize, args.resize]),
        transforms.ToTensor(),
        ]

    transforms_compose_test = [
        transforms.Resize([args.resize, args.resize]),
        transforms.ToTensor(),
        ]

    train_data = LontarDataset(transform=transforms.Compose(transforms_compose))

    test_data = datasets.ImageFolder(
        root='lontar_dataset/test_image',
        transform=transforms.Compose(transforms_compose_test))

    sampler = weights.weighted_random_sampler()

    train_loader = DataLoader(dataset=train_data, batch_size=args.batch_size,
                          num_workers=args.workers, pin_memory=True, sampler=sampler)
    test_loader = DataLoader(dataset=test_data, batch_size=args.batch_size,
                            shuffle=False, num_workers=args.workers, pin_memory=True)
    val_loader = DataLoader(dataset=test_data, batch_size=args.batch_size,
                            shuffle=True, num_workers=args.workers, pin_memory=True)

    # define loss function (criterion) and optimizer
    criterion = nn.CrossEntropyLoss().cuda()

    if args.half:
        model.half()
        criterion.half()

    optimizer = torch.optim.SGD(model.parameters(), args.lr,
                                momentum=args.momentum,
                                weight_decay=args.weight_decay)

    lr_scheduler = torch.optim.lr_scheduler.MultiStepLR(optimizer,
                                                        milestones=[100, 150], last_epoch=args.start_epoch - 1)

    if args.arch in ['resnet1202', 'resnet110']:
        # for resnet1202 original paper uses lr=0.01 for first 400 minibatches for warm-up
        # then switch back. In this setup it will correspond for first epoch.
        for param_group in optimizer.param_groups:
            param_group['lr'] = args.lr*0.1


    if args.evaluate:
        validate(val_loader, model, criterion)
        return

    torch.cuda.synchronize()
    times = []

    for epoch in range(args.start_epoch, args.epochs):

        start_epoch = time.time()

        # train for one epoch
        print('current lr {:.5e}'.format(optimizer.param_groups[0]['lr']))
        data.append(train(train_loader, model, criterion, optimizer, epoch))
        losses.append(data[epoch])

        lr_scheduler.step()

        end_epoch = time.time()
        elapsed = end_epoch - start_epoch
        times.append(elapsed)

        # evaluate on validation set
        prec1, prec5 = validate(val_loader, model, criterion)
        err1 = 100-prec1
        err5 = 100-prec5

        err1s.append(err1)
        err5s.append(err5)

        # remember best prec@1 and save checkpoint
        is_best = prec1 > best_prec1
        best_prec1 = max(prec1, best_prec1)
        best_prec5 = max(prec5, best_prec5)
        best_err1 = 100-prec1
        best_err5 = 100-prec5
        print('Current Best Prec @1: {best_prec1:.3f} (Err: {best_err1:.3f} ) | '
              '@5: {best_prec5:.3f} (Err: {best_err5:.3f} )\n'
              .format(epoch, best_prec1=best_prec1, best_err1=best_err1, best_prec5=best_prec5, best_err5=best_err5))
        best_err1s.append(100-best_prec1)
        best_err5s.append(100-best_prec5)

        if epoch > 0 and epoch % args.save_every == 0:
            save_checkpoint({
                'epoch': epoch + 1,
                'state_dict': model.state_dict(),
                'best_prec1': best_prec1,
            }, is_best, filename=os.path.join(args.save_dir, 'checkpoint.th'))

        save_checkpoint({
            'state_dict': model.state_dict(),
            'best_prec1': best_prec1,
        }, is_best, filename=os.path.join(args.save_dir, 'model.th'))

    current_device = torch.cuda.current_device()
    device_name = torch.cuda.get_device_name(0)

    avg_time = sum(times)/args.epochs
    sum_time = sum(times)

    print(device_name)
    print('Training took {} seconds (avg. {} per epoch).\n'
          'The training accuracy from {} model after {} epochs is: \n'
          'Prec@1 = {acc1:.3f}\n'
          'Prec@5 = {acc5:.3f}'.format(
           sum_time, avg_time, args.arch, args.epochs, acc1 = best_prec1, acc5 = best_prec5))

def train(train_loader, model, criterion, optimizer, epoch):
    """
        Run one train epoch
    """
    batch_time = AverageMeter()
    data_time = AverageMeter()
    losses = AverageMeter()
    top1 = AverageMeter()
    top5 = AverageMeter()

    # switch to train mode
    model.train()

    end = time.time()
    for i, (input, target) in enumerate(train_loader):

        # measure data loading time
        data_time.update(time.time() - end)

        target = target.cuda()
        input_var = input.cuda()
        target_var = target
        if args.half:
            input_var = input_var.half()

        # compute output
        output = model(input_var)
        loss = criterion(output, target_var)

        # compute gradient and do SGD step
        optimizer.zero_grad()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 10)
        loss.backward()
        optimizer.step()

        output = output.float()
        loss = loss.float()

        # measure accuracy and record loss
        prec1, prec5 = accuracy(output.data, target, topk=(1, 5))
        losses.update(loss.item(), input.size(0))
        top1.update(prec1.item(), input.size(0))
        top5.update(prec5.item(), input.size(0))

        # measure elapsed time
        batch_time.update(time.time() - end)
        end = time.time()

        if i % args.print_freq == 0:
            print('Epoch: [{0}][{1}/{2}] | '
                  'Time {batch_time.val:.3f} ({batch_time.avg:.3f}) | '
                  'Data {data_time.val:.3f} ({data_time.avg:.3f}) | '
                  'Loss {loss.val:.4f} ({loss.avg:.4f}) | '
                  'Prec@1 {top1.val:.3f} ({top1.avg:.3f}) | '
                  'Prec@5 {top5.val:.3f} ({top5.avg:.3f})\n'.format(
                      epoch, i, len(train_loader), batch_time=batch_time,
                      data_time=data_time, loss=losses, top1=top1, top5=top5))
        
        return losses.val

def validate(val_loader, model, criterion):
    """
    Run evaluation
    """
    batch_time = AverageMeter()
    losses = AverageMeter()
    top1 = AverageMeter()
    top5 = AverageMeter()

    # switch to evaluate mode
    model.eval()

    end = time.time()
    with torch.no_grad():
        for i, (input, target) in enumerate(val_loader):
            target = target.cuda()
            input_var = input.cuda()
            target_var = target.cuda()

            if args.half:
                input_var = input_var.half()

            # compute output
            output = model(input_var)
            loss = criterion(output, target_var)

            output = output.float()
            loss = loss.float()

            # measure accuracy and record loss
            prec1, prec5 = accuracy(output.data, target, topk=(1, 5))
            losses.update(loss.item(), input.size(0))
            top1.update(prec1.item(), input.size(0))
            top5.update(prec5.item(), input.size(0))

            # measure elapsed time
            batch_time.update(time.time() - end)
            end = time.time()

            if i % args.print_freq == 0:
                print('Test: [{0}/{1}]\t'
                      'Time {batch_time.val:.3f} ({batch_time.avg:.3f})\t'
                      'Loss {loss.val:.4f} ({loss.avg:.4f})\t'
                      'Prec@1 {top1.val:.3f} ({top1.avg:.3f})'.format(
                          i, len(val_loader), batch_time=batch_time, loss=losses,
                          top1=top1))

    print('Test\t  Prec@1: {top1.avg:.3f} (Err: {error1:.3f} )\n'
          'Test\t  Prec@5: {top5.avg:.3f} (Err: {error5:.3f} )'
          .format(top1=top1, error1=100-top1.avg, top5=top5, error5=100-top5.avg))

    return top1.avg, top5.avg

def save_checkpoint(state, is_best, filename='checkpoint.pth.tar'):
    """
    Save the training model
    """
    torch.save(state, filename)

class AverageMeter(object):
    """Computes and stores the average and current value"""
    def __init__(self):
        self.reset()

    def reset(self):
        self.val = 0
        self.avg = 0
        self.sum = 0
        self.count = 0

    def update(self, val, n=1):
        self.val = val
        self.sum += val * n
        self.count += n
        self.avg = self.sum / self.count

def accuracy(output, target, topk=(1,)):
    """Computes the precision@k for the specified values of k"""
    maxk = max(topk)
    batch_size = target.size(0)

    _, pred = output.topk(maxk, 1, True, True)
    pred = pred.t()
    correct = pred.eq(target.reshape(1, -1).expand_as(pred))

    res = []
    for k in topk:
        correct_k = correct[:k].reshape(-1).float().sum(0)
        res.append(correct_k.mul_(100.0 / batch_size))
    return res

if __name__ == '__main__':
    main()
