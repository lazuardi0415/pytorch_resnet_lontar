import pandas as pd
import numpy as np
from torch.utils.data import WeightedRandomSampler

def weighted_random_sampler():
    df = pd.read_csv('lontar_dataset\\train_labels.csv')
    labels = np.array(df.values.tolist())
    classes = labels[:,1].astype(int)
    class_sample_count = np.array(
        [
            len(np.where(labels == t)[0]) for t in np.unique(labels[:,1])
        ])
    weight = 1. / class_sample_count
    samples_weight = np.array([weight[t] for t in classes])
    sampler = WeightedRandomSampler(samples_weight, len(samples_weight))
    
    return sampler