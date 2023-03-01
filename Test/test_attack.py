# -*- encoding: utf-8 -*-
'''
@File    :   test_attack.py
@Modify time      @Author    @Version    @Description
------------      -------    --------    -----------
2022/11/5 20:16   leoy         1.0         none
'''
# import torch
# from torch.autograd import Variable
# from torchvision import utils
from PIL import Image
from torchvision import transforms
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import random
import time
import os
import torch
from DataSets import setup_mnist  # MNISTModel
from Models import lenet
from Attack import CarliniL2
from Evaluation import evaluation

import logging

logging.basicConfig(filename='result.log',
                    level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s -  %(message)s')
logging.disable(logging.DEBUG)


def show(img):
    """
    Show MNSIT digits in the console.
    """
    remap = "  .*#" + "#" * 100
    img = (img.flatten() + .5) * 3
    if len(img) != 784:
        return
    print("START")
    for i in range(28):
        print("".join([remap[int(round(x))] for x in img[i * 28:i * 28 + 28]]))


def generate_data(data, samples, targeted=True, start=0, inception=False):
    """
    Generate the input data to the attack algorithm.

    data: the images to attack
    samples: number of samples to use
    targeted: if true, construct targeted attacks, otherwise untargeted attacks
    start: offset into data to use
    inception: if targeted and inception, randomly sample 100 targets intead of 1000
    """
    inputs = []
    targets = []
    origin_label = []
    for i in range(samples):
        if targeted:
            if inception:
                seq = random.sample(range(1, 1001), 10)
            else:
                seq = range(data.test_labels.shape[1])

            for j in seq:
                if (j == np.argmax(data.test_labels[start + i])) and (inception == False):
                    continue
                inputs.append(data.test_data[start + i])
                targets.append(np.eye(data.test_labels.shape[1])[j])
                origin_label.append(data.test_labels[start + i])
        else:
            inputs.append(data.test_data[start + i])
            targets.append(data.test_labels[start + i])
            origin_label.append(data.test_labels[start + i])

    inputs = np.array(inputs)
    targets = np.array(targets)
    origin_label = np.array(origin_label)

    return inputs, targets, origin_label


def distortion(a, b, norm_type='l2'):
    if norm_type == 'l1':
        return np.sum(np.abs(a - b))

    elif norm_type == 'l2':
        return np.sum((a - b) ** 2) ** .5

    elif norm_type == 'li':
        return np.amax(np.abs(a - b))
    else:
        return None


def create_attack(model, attack_type='l2'):
    if attack_type == 'l1':
        return None

    elif attack_type == 'l2':
        return CarliniL2.CarliniL2(model, (9, 1, 28, 28), max_iterations=1000, confidence=0)

    elif attack_type == 'li':
        return None
    else:
        return None


def run(samples=10, targeted=True, attack_type='l2'):
    # add algorithm configuration as the param : config.
    start = 5
    inception = False
    model_path = r'../Models/models/mnist.pth'
    # prepare the data and model for attack, use param : model
    data = setup_mnist.MNIST()
    model = lenet.LeNet(in_channels=1, out_size=1152)
    model.load_state_dict(torch.load(model_path))
    # prepare attack and inputs data.
    attack = create_attack(model, attack_type=attack_type)
    inputs, targets, origin_label = generate_data(data, samples=samples, targeted=targeted,
                                    start=start, inception=inception)

    # attack
    timeStart = time.time()
    adv = attack.attack(inputs, targets)
    timeEnd = time.time()
    print("Took", timeEnd - timeStart, "seconds to run", len(inputs), "samples.")
    adv_img = np.transpose(adv, [0, 3, 1, 2])
    predicts = []
    # evaluation
    for i in range(len(adv)):
        print("Adversarial:")
        show(adv[i])
        print("target class: ", np.argmax(targets[i]))

        outputs = model(torch.tensor(adv_img[i:i+1]))
        predict = torch.max(outputs, dim=1)[1].data.numpy()
        predicts.append(outputs.detach().numpy()[0])
        print(outputs.detach().numpy())
        print("Classification:", predict)
        print("Total distortion:", np.sum((adv[i] - inputs[i]) ** 2) ** .5)

    # evaluation with the indicator
    print('--------evaluation----------')
    evalue = evaluation.Evaluation(inputs, adv, origin_label, targets, np.array(predicts), True)
    print("Evaluation indicator:")
    print(evalue.evaluation())

if __name__ == "__main__":
    run(samples=1, targeted=True, attack_type='l2')
