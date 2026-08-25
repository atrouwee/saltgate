# Third-party notices

SALTGATE itself is MIT (see `LICENSE`). Two machine-learning models it uses are
other people's work, and their terms travel with them. This file is the notice
BSD-3-Clause requires, and the provenance record for anyone who needs to know
what is inside the tool.

---

## 1. Auto-rotation backbone — ResNet-50 (torchvision)

**Used for:** deciding which way up a scanned frame goes, together with the face
detector below. Runs as ONNX through OpenCV; SALTGATE contains no training code
for it and does not modify the weights.

| | |
|---|---|
| Source project | [torchvision](https://github.com/pytorch/vision) |
| Weights | `ResNet50_Weights.IMAGENET1K_V2` |
| Original file | https://download.pytorch.org/models/resnet50-11ad3fa6.pth |
| Training data | ImageNet-1K |
| Recipe | https://github.com/pytorch/vision/issues/3995#issuecomment-1013906621 |
| Licence | BSD-3-Clause (reproduced below) |

**What SALTGATE changed.** The classifier head and global pool are removed, so
only the frozen convolutional stack remains; the graph is exported to ONNX at
batch 1 and stored in float16. The weight *values* are torchvision's, unchanged
beyond that precision conversion. Verified against the original on 80 frames:
identical rotation chosen 80/80, largest probability difference 3.1e-3.
Redistributed as `orient-resnet50-body-fp16.onnx`, sha256 `818e29fe77ea228d64fcf04f7798c98f4838a7a66385209c70785472321b2a49`.

**A note on ImageNet.** These weights were trained on ImageNet-1K, whose terms
of access are granted for non-commercial research and educational use.
Redistribution of ImageNet-pretrained weights is standard practice across the
field, and whether a trained model inherits those terms is not settled law.
This notice records the provenance so that anyone with a stricter requirement
can make their own decision. SALTGATE is free software and sells nothing.

### torchvision licence

```
BSD 3-Clause License

Copyright (c) Soumith Chintala 2016, 
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice, this
  list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.

* Neither the name of the copyright holder nor the names of its
  contributors may be used to endorse or promote products derived from
  this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```

---

## 2. Face detector — YuNet

**Used for:** scoring which of the four rotations puts faces the right way up.
Shipped inside the package as `face_detection_yunet_2023mar.onnx` (232 KB) and
loaded through OpenCV's `cv2.FaceDetectorYN`.

| | |
|---|---|
| Source project | [OpenCV Zoo](https://github.com/opencv/opencv_zoo) — `models/face_detection_yunet` |
| File | `face_detection_yunet_2023mar.onnx`, unmodified |
| Authors | Shiqi Yu, Yuantao Feng and contributors (Southern University of Science and Technology) |
| Licence | MIT |

### YuNet licence (MIT)

```
MIT License

Copyright (c) Shiqi Yu, Yuantao Feng and contributors (OpenCV Zoo,
Southern University of Science and Technology)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

MIT permits commercial and non-commercial use, modification and redistribution,
on the condition that this notice travels with substantial portions of the
software — which is what this file is for. The model is used unmodified.
