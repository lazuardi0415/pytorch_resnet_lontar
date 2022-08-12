import torch
import torchvision.transforms as transforms

def get_mean_and_std(dataloader):
    channels_sum, channels_squared_sum, num_batches = 0, 0, 0
    for data, _ in dataloader:
        # Mean over batch, height and width, but not over the channels
        #if grayscale:
            #channels_sum += torch.mean(data)
            #channels_squared_sum += torch.mean(data**2)
        #else:
        channels_sum += torch.mean(data, dim=[0, 2, 3])
        channels_squared_sum += torch.mean(data**2, dim=[0, 2, 3])
            
        num_batches += 1
        
    mean = channels_sum / num_batches

    # std = sqrt(E[X^2] - (E[X])^2)
    std = (channels_squared_sum / num_batches - mean ** 2) ** 0.5

    return mean, std

transforms_norm_rgb = [
    transforms.ToPILImage(),
    transforms.Resize(resize),
    transforms.ToTensor()
    ]

transforms_norm_rgb_ac = [
    transforms.ToPILImage(),
    transforms.Resize(resize),
    transforms.ToTensor(),
    transforms.RandomAutocontrast(p=1.0)
    ]

transforms_norm_rgb_gauss = [
    transforms.ToPILImage(),
    transforms.Resize(resize),
    transforms.ToTensor(),
    GaussBlur()
    ]

transforms_norm_rgb_ac_gauss = [
    transforms.ToPILImage(),
    transforms.Resize(resize),
    transforms.ToTensor(),
    transforms.RandomAutocontrast(p=1.0),
    GaussBlur()
    ]

transforms_norm_gray = [
    transforms.ToPILImage(),
    transforms.Resize(resize),
    transforms.ToTensor(),
    transforms.Grayscale()
    ]

transforms_norm_gray_ac = [
    transforms.ToPILImage(),
    transforms.Resize(resize),
    transforms.ToTensor(),
    transforms.Grayscale(),
    transforms.RandomAutocontrast(p=1.0)
    ]

transforms_norm_gray_gauss = [
    transforms.ToPILImage(),
    transforms.Resize(resize),
    transforms.ToTensor(),
    transforms.Grayscale(),
    GaussBlur()
    ]

transforms_norm_gray_ac_gauss = [
    transforms.ToPILImage(),
    transforms.Resize(resize),
    transforms.ToTensor(),
    transforms.Grayscale(),
    transforms.RandomAutocontrast(p=1.0),
    GaussBlur()
    ]

transforms_composes = [transforms_norm_rgb, transforms_norm_rgb_ac, transforms_norm_rgb_gauss, transforms_norm_rgb_ac_gauss, transforms_norm_gray, transforms_norm_gray_ac, transforms_norm_gray_gauss, transforms_norm_gray_ac_gauss]

for transforms_compose in transforms_composes:
    train_data_norm = LontarDataset(transform=transforms.Compose(transforms_compose))
    train_loader_norm = DataLoader(dataset=train_data_norm, batch_size=len(train_data_norm), num_workers=num_workers)
    dataset_mean, dataset_std = get_mean_and_std(train_loader_norm)
    print(f"mean={dataset_mean}, std={dataset_std}")