"""
The 18-layer ResNet network
===========================
Layer Name     Layer-config
===========================
conv1          7X7, 64, stride 2 
--------------------------------
               3X3 max pool, stride 2
               -----------------
                   +---------
               ---    ---   |  
               | 3X3, 64|   |
conv2_x        | 3X3, 64|   | X 2
               ---    ---   |
                   +<--------
---------------------------------
                   +---------
               ---     ---  |
               | 3X3, 128|  |
conv3_x        | 3X3, 128|  | X 2
               ---     ---  |
                   +<--------
---------------------------------
                   +---------
               ---     ---  |
               | 3X3, 256|  |
conv4_x        | 3X3, 256|  | X 2
               +--     ---  |
                   +<--------
---------------------------------
                   +---------
               ---     ---  |
               | 3X3, 512|  |
conv5_x        | 3X3, 512|  | X 2
               ---     ---  |
                   +<--------
---------------------------------
               avg pool, 1000-d, fc 
               + softmax
---------------------------------
"""

import torch.nn as nn
import torch.utils.model_zoo as model_zoo

def conv3x3(in_planes, out_planes, stride=1):
    """3x3 convolution with padding"""
    return nn.Conv2d(in_planes, out_planes, kernel_size=3, stride=stride,
                     padding=1, bias=False)


def conv1x1(in_planes, out_planes, stride=1):
    """1x1 convolution"""
    return nn.Conv2d(in_planes, out_planes, kernel_size=1, stride=stride, bias=False)


"""
           | 64-d
           |------------
           |           |
           v           |
   +--------------+    |
   |  3 x 3, 64   |    |
   +--------------+    |
           | ReLu      |
           v           |
   +--------------+    |
   |  3 x 3, 64   |    |
   +--------------+    |
           |           |
           v           |
          ---          |
          |+|<----------
          ---
           | ReLu
           v
"""

class BasicBlock(nn.Module):
    expansion = 1

    def __init__(self, inplanes, planes, stride=1, downsample=None):
        super(BasicBlock, self).__init__()
        self.conv1 = conv3x3(inplanes, planes, stride)
        self.bn1 = nn.BatchNorm2d(planes)
        self.relu = nn.ReLU(inplace=True)
        self.conv2 = conv3x3(planes, planes)
        self.bn2 = nn.BatchNorm2d(planes)
        self.downsample = downsample
        self.stride = stride

    def forward(self, x):
        identity = x

        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)

        out = self.conv2(out)
        out = self.bn2(out)

        if self.downsample is not None:
            identity = self.downsample(x)

        out += identity
        out = self.relu(out)

        return out

"""
           | 256-d
           +-----------+
           |           |
           v           |
   +--------------+    |
   |  1 x 1, 64   |    |
   +--------------+    |
           | ReLu      |
           v           |
   +--------------+    |
   |  3 x 3, 64   |    |
   +--------------+    v
           | ReLu      |
           v           |
   +--------------+    |
   |  1 x 1, 256  |    |
   +--------------+    |
           |           |
           v           |
          +-+          |
          |+|<---------+
          +-+
           | ReLu
           v
"""

class BottleneckBlock(nn.Module):
    expansion = 4

    def __init__(self, inplanes, planes, stride=1, downsample=None):
        super(BottleneckBlock, self).__init__()
        self.conv1 = conv1x1(inplanes, planes)
        self.bn1 = nn.BatchNorm2d(planes)
        self.conv2 = conv3x3(planes, planes, stride)
        self.bn2 = nn.BatchNorm2d(planes)
        self.conv3 = conv1x1(planes, planes * self.expansion)
        self.bn3 = nn.BatchNorm2d(planes * self.expansion)
        self.relu = nn.ReLU(inplace=True)
        self.downsample = downsample
        self.stride = stride

    def forward(self, x):
        identity = x

        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)

        out = self.conv2(out)
        out = self.bn2(out)
        out = self.relu(out)

        out = self.conv3(out)
        out = self.bn3(out)

        if self.downsample is not None:
            identity = self.downsample(x)

        out += identity
        out = self.relu(out)

        return out


class ResNet(nn.Module):

    def __init__(self, block, stacked_block_counts, num_classes=10, zero_init_residual=False):
        super(ResNet, self).__init__()
        self.inplanes = 64
        self.conv1 = nn.Conv2d(3, 64, kernel_size=7, stride=2, padding=3,
                               bias=False)
        self.bn1 = nn.BatchNorm2d(64)
        self.relu = nn.ReLU(inplace=True)
        self.maxpool = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)
        self.layer1 = self._make_layer(block, 64, stacked_block_counts[0])
        self.layer2 = self._make_layer(block, 128, stacked_block_counts[1], stride=2)
        self.layer3 = self._make_layer(block, 256, stacked_block_counts[2], stride=2)
        self.layer4 = self._make_layer(block, 512, stacked_block_counts[3], stride=2)
        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
        self.fc = nn.Linear(512 * block.expansion, num_classes)

        # Zero-initialize the last BN in each residual branch,
        # so that the residual branch starts with zeros, and each residual block behaves like an identity.
        # This improves the model by 0.2~0.3% according to https://arxiv.org/abs/1706.02677
        if zero_init_residual:
            for m in self.modules():
                if isinstance(m, BottleneckBlock):
                    nn.init.constant_(m.bn3.weight, 0)
                elif isinstance(m, BasicBlock):
                    nn.init.constant_(m.bn2.weight, 0)

    def _make_layer(self, block, planes, block_count, stride=1):
        downsample = None
        if stride != 1 or self.inplanes != planes * block.expansion:
            downsample = nn.Sequential(
                conv1x1(self.inplanes, planes * block.expansion, stride),
                nn.BatchNorm2d(planes * block.expansion),
            )

        stacked_blocks = []
        stacked_blocks.append(block(self.inplanes, planes, stride, downsample))
        self.inplanes = planes * block.expansion
        for _ in range(1, block_count):
            stacked_blocks.append(block(self.inplanes, planes))

        return nn.Sequential(*stacked_blocks)

    def forward(self, x):
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.maxpool(x)

        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)

        x = self.avgpool(x)
        x = x.view(x.size(0), -1)
        x = self.fc(x)

        return x




