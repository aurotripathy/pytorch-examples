"""
Runs all combinations of specified activations with specified optimizers.
Network is Lenet5, dataset is mnist
"""

from lenet import LeNet5
import torch
import torch.nn as nn
import torch.optim as optim
from torchvision.datasets.mnist import MNIST
import torchvision.transforms as transforms
from torch.utils.data import DataLoader
# from pudb import set_trace

data_train = MNIST('./data/mnist',
                   download=True,
                   transform=transforms.Compose([
                       transforms.Resize((32, 32)),
                       transforms.ToTensor(),
                       transforms.Normalize((0.1307,), (0.3081,))
                   ]))
data_test = MNIST('./data/mnist',
                  train=False,
                  download=True,
                  transform=transforms.Compose([
                      transforms.Resize((32, 32)),
                      transforms.ToTensor(),
                      transforms.Normalize((0.1307,), (0.3081,))
                  ]))
data_train_loader = DataLoader(data_train, batch_size=256, shuffle=True, num_workers=8)
data_test_loader = DataLoader(data_test, batch_size=1024, num_workers=8)


criterion = nn.CrossEntropyLoss()  # keep this constant and vary the activations and optims
device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
print("Using device: ", device)

def train(epoch, net, optimizer):

    net.train()
    for i, (images, labels) in enumerate(data_train_loader):
        images = images.to(device)
        labels = labels.to(device)

        optimizer.zero_grad()
        output = net(images)
        loss = criterion(output, labels)
        loss.backward()
        optimizer.step()

        # if i % 10 == 0:
        #     print('Train - Epoch %d, Batch: %d, Loss: %f' % (epoch, i,
        #                                                      loss.detach().cuda().item()))


def test(epoch, net):
    net.eval()
    total_correct = 0
    avg_loss = 0.0
    for _, (images, labels) in enumerate(data_test_loader):
        images = images.to(device)
        labels = labels.to(device)
        output = net(images)
        avg_loss += criterion(output, labels).sum()
        pred = output.detach().max(1)[1]
        total_correct += pred.eq(labels.view_as(pred)).sum()

    avg_loss /= len(data_test)
    print('Epoch %d, Avg. Test Loss: %f, Accuracy: %f' % (epoch, avg_loss.detach().cuda().item(),
                                                          float(total_correct) / len(data_test)))


def train_and_test(epoch, net, optimizer):

    train(epoch, net, optimizer)
    test(epoch, net)

nb_epochs = 15
def setup_run(optimizer_str, activation_str):
    net = LeNet5(activation_str).cuda()

    if optimizer_str == 'SGD' and activation_str == 'Sigmoid':
        optimizer = optim.SGD(net.parameters(), lr=0.01,  # different learning rate
                              momentum=0.9, nesterov=True)
    elif optimizer_str == 'Adam' and activation_str == 'Sigmoid':
        optimizer = optim.Adam(net.parameters(), lr=0.01)
    elif optimizer_str == 'Adam':
        optimizer = optim.Adam(net.parameters(), lr=2e-3)
    elif optimizer_str == 'SGD':
        optimizer = optim.SGD(net.parameters(), lr=2e-3, momentum=0.9)
    elif optimizer_str == 'RMSprop':
        optimizer = optim.RMSprop(net.parameters(), lr=2e-3, momentum=0.9)
    else:
        print("***Unknown optimizer:", optimizer_str)
        exit(2)

    for epoch in range(1, nb_epochs + 1):
        train_and_test(epoch, net, optimizer)

if __name__ == '__main__':
    activation_strs = ['SoftExponential', 'Sigmoid', 'SiLU', 'GeLU', 'ReLU', 'Tanh', 'ELU', 'LeakyReLU']
    optimizer_strs = ['SGD', 'RMSprop', 'Adam']
    for activation_str in activation_strs:
        for optimizer_str in optimizer_strs:
            print('...Training with optimizer, {} and activation, {}'.format(optimizer_str,activation_str))
            setup_run(optimizer_str, activation_str)
