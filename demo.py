import torch
from torch.autograd import Variable
import tools.utils as utils
import tools.dataset as dataset
from PIL import Image
from collections import OrderedDict
import numpy as np
import cv2
from models.moran import MORAN
import time

model_path = './demo.pth'
img_path = './demo/14.jpg'
alphabet = '0:1:2:3:4:5:6:7:8:9:a:b:c:d:e:f:g:h:i:j:k:l:m:n:o:p:q:r:s:t:u:v:w:x:y:z:$'

moran = MORAN(1, len(alphabet.split(':')), 256, 32, 100, BidirDecoder=True, inputDataType='torch.FloatTensor')

if torch.cuda.is_available():
    moran = moran.cuda()

print('loading pretrained model from %s' % model_path)
if torch.cuda.is_available():
    state_dict = torch.load(model_path)
else:
    state_dict = torch.load(model_path, map_location='cpu')
MORAN_state_dict_rename = OrderedDict()
for k, v in state_dict.items():
    name = k.replace("module.", "") # remove `module.`
    MORAN_state_dict_rename[name] = v
moran.load_state_dict(MORAN_state_dict_rename)

for p in moran.parameters():
    p.requires_grad = False
moran.eval()

start = time.time()
converter = utils.strLabelConverterForAttention(alphabet, ':')
transformer = dataset.resizeNormalize((100, 32))
image = Image.open(img_path).convert('L')
image = transformer(image)

if torch.cuda.is_available():
    image = image.cuda()
image = image.view(1, *image.size())
image = Variable(image)
text = torch.LongTensor(1 * 5)
length = torch.IntTensor(1)
text = Variable(text)
length = Variable(length)

max_iter = 20
t, l = converter.encode('0'*max_iter)
utils.loadData(text, t)
utils.loadData(length, l)
output = moran(image, length, text, text, test=True, debug=True)
# stop = time.time()

preds, preds_reverse = output[0]
rectified = output[1][0].numpy().transpose([1, 2, 0]) # BCHW tensor to HWC array
demo = output[2]

_, preds = preds.max(1)
_, preds_reverse = preds_reverse.max(1)

sim_preds = converter.decode(preds.data, length.data)
sim_preds = sim_preds.strip().split('$')[0]
sim_preds_reverse = converter.decode(preds_reverse.data, length.data)
sim_preds_reverse = sim_preds_reverse.strip().split('$')[0]

stop = time.time()
print('\nused time: {}'.format(stop-start))
print('\nResult:\n' + 'Left to Right: ' + sim_preds + '\nRight to Left: ' + sim_preds_reverse + '\n\n')

# cv2.imshow("demo", demo)
# cv2.waitKey()
cv2.imwrite('demo/res-demo.png', demo)
cv2.imwrite('demo/res.png', (255*rectified).astype(dtype=np.uint8))