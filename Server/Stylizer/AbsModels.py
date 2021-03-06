import torch 
from torch import nn
import torch.nn.functional as F
import torchvision.transforms as transforms
from PIL import Image


class Encoder(nn.Module):
    def __init__(self):
        super(Encoder,self).__init__()
        self.ins0 = nn.InstanceNorm2d(3,affine=True)
        self.rpad = nn.ReflectionPad2d(15)
        self.conv1 = nn.Conv2d(3,32,kernel_size=3,stride=1)
        self.ins1 = nn.InstanceNorm2d(32,affine=True)
        self.conv2 = nn.Conv2d(32,32,kernel_size=3,stride=2)
        self.ins2 = nn.InstanceNorm2d(32,affine=True)
        self.conv3 = nn.Conv2d(32,64,kernel_size=3,stride=2)
        self.ins3 = nn.InstanceNorm2d(64,affine=True)
        self.conv4 = nn.Conv2d(64,128,kernel_size=3,stride=2)
        self.ins4 = nn.InstanceNorm2d(128,affine=True)
        self.conv5 = nn.Conv2d(128,256,kernel_size=3,stride=2)
        self.ins5 = nn.InstanceNorm2d(256,affine=True)
        self.relu = torch.nn.ReLU()
        
    def forward(self,x):
        x = self.ins0(x)
        x = self.rpad(x)
        x = self.relu(self.ins1(self.conv1(x)))
        x = self.relu(self.ins2(self.conv2(x)))
        x = self.relu(self.ins3(self.conv3(x)))
        x = self.relu(self.ins4(self.conv4(x)))
        x = self.relu(self.ins5(self.conv5(x)))
        return x

class ResidualBlock(torch.nn.Module):
    def __init__(self, channels):
        super(ResidualBlock, self).__init__()
        self.rpad = nn.ReflectionPad2d(1)
        self.conv1 = nn.Conv2d(channels, channels, kernel_size=3, stride=1)
        self.in1 = torch.nn.InstanceNorm2d(channels, affine=True)
        self.conv2 = nn.Conv2d(channels, channels, kernel_size=3, stride=1)
        self.in2 = nn.InstanceNorm2d(channels, affine=True)
        self.relu = nn.ReLU()

    def forward(self, x):
        residual = x
        out = self.rpad(x)
        out = self.relu(self.in1(self.conv1(out)))
        out = self.in2(self.conv2(self.rpad(out)))
        out = out + residual
        return out
    
class TransforBlock(nn.Module): #different from tf implementation but same as paper
    def __init__(self):
        super(TransforBlock,self).__init__()
        self.rpad = nn.ReflectionPad2d(4)
        self.conv = nn.AvgPool2d(kernel_size=10,stride=1) #nn.Conv2d(3,1,kernel_size=10,stride=1)
    
    def forward(self,x):
        return self.rpad(self.conv(x))

class Decoder(nn.Module):
    def __init__(self):
        super(Decoder,self).__init__()
        self.res1 = ResidualBlock(256)
        self.res2 = ResidualBlock(256)
        self.res3 = ResidualBlock(256)
        self.res4 = ResidualBlock(256)
        self.res5 = ResidualBlock(256)
        self.res6 = ResidualBlock(256)
        self.res7 = ResidualBlock(256)
        self.res8 = ResidualBlock(256)
        self.res9 = ResidualBlock(256)
        
        self.upconv1 = nn.Conv2d(256,256,kernel_size=3,stride=1)
        self.ins1 = nn.InstanceNorm2d(256,affine=True)
        self.upconv2 = nn.Conv2d(256,128,kernel_size=3,stride=1)
        self.ins2 = nn.InstanceNorm2d(128,affine=True)
        self.upconv3 = nn.Conv2d(128,64,kernel_size=3,stride=1)
        self.ins3 = nn.InstanceNorm2d(64,affine=True)
        self.upconv4 = nn.Conv2d(64,32,kernel_size=3,stride=1)
        self.ins4 = nn.InstanceNorm2d(32,affine=True)
        self.rpad = nn.ReflectionPad2d(3)
        self.upconv5 = nn.Conv2d(32,3,kernel_size=7,stride=1)
        
        self.relu = nn.ReLU()
        self.sig = nn.Sigmoid()
        self.zpad = nn.ZeroPad2d(1)
        
    def forward(self,x):
        x = self.res1(x)
        x = self.res2(x)
        x = self.res3(x)
        x = self.res4(x)
        x = self.res5(x)
        x = self.res6(x)
        x = self.res7(x)
        x = self.res8(x)
        x = self.res9(x)
        
        x = self.relu(self.ins1(self.upconv1(self.zpad(F.interpolate(x,scale_factor=2)))))
        x = self.relu(self.ins2(self.upconv2(self.zpad(F.interpolate(x,scale_factor=2)))))
        x = self.relu(self.ins3(self.upconv3(self.zpad(F.interpolate(x,scale_factor=2)))))
        x = self.relu(self.ins4(self.upconv4(self.zpad(F.interpolate(x,scale_factor=2)))))
        
        x = self.rpad(x)
        x = self.sig(self.upconv5(x))*2. - 1.
        return x


MODELS = ['cezanne','el-greco','monet','picasso','van-gogh']

enc = Encoder().cuda().eval()
dec = Decoder().cuda().eval()
state_dicts = {}
for mod in MODELS:
    state_dicts[f"{mod}e"] = torch.load(f"weights/model_{mod}/enc.pth")
    state_dicts[f"{mod}d"] = torch.load(f"weights/model_{mod}/dec.pth")

print("Enc/dec instantiated....")

def stylizeAbstract(Ic,info):
    enc.load_state_dict(state_dicts[f"{info['model_name']}e"])
    dec.load_state_dict(state_dicts[f"{info['model_name']}d"])
    img = transforms.ToTensor()(Ic)
    arr = img.unsqueeze(0).cuda()
    arr = arr * 2 - 1

    with torch.no_grad():
        f = enc(arr)
        arr = dec(f)

    arr = (arr + 1) / 2
    arr -= arr.min()
    arr /= arr.max()
    arr = arr.squeeze(0).cpu().numpy().transpose(1, 2, 0) * 255
    return Image.fromarray(arr.clip(0, 255).astype("uint8"))