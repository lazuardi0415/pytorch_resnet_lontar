#!/bin/bash

for model in resnet20
do
    python -u trainer.py  --arch=$model  --epochs=1  --save-dir=save_$model |& tee -a "logs\log_$model.log"
done