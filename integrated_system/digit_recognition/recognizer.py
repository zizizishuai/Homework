import os
import time
import torch
import numpy as np
from PIL import Image, ImageOps, ImageFilter
from model import CNN, MLP

class DigitRecognizer:
    """数字识别器类"""
    def __init__(self, model_path='./models/mnist_model.pth'):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = None
        self.model_type = None
        self.load_model(model_path)

    def load_model(self, model_path):
        """加载训练好的模型"""
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"模型文件不存在: {model_path}")

        checkpoint = torch.load(model_path, map_location=self.device)
        self.model_type = checkpoint.get('model_type', 'CNN')

        if self.model_type == 'CNN':
            self.model = CNN().to(self.device)
        else:
            self.model = MLP().to(self.device)

        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.model.eval()
        print(f"模型加载成功: {self.model_type}")

    def _center_and_resize(self, img: Image.Image) -> Image.Image:
        img = img.convert('L')
        img = img.filter(ImageFilter.MedianFilter(size=3))
        img_np = np.array(img, dtype=np.uint8)

        if img_np.mean() > 127:
            img = ImageOps.invert(img)
            img_np = np.array(img, dtype=np.uint8)

        threshold = 128
        binary = img_np > threshold
        coords = np.column_stack(np.where(binary))
        if coords.size > 0:
            y_min, x_min = coords.min(axis=0)
            y_max, x_max = coords.max(axis=0)
            img = img.crop((x_min, y_min, x_max + 1, y_max + 1))

        img.thumbnail((20, 20), Image.Resampling.LANCZOS)

        new_img = Image.new('L', (28, 28), color=0)
        x_offset = (28 - img.width) // 2
        y_offset = (28 - img.height) // 2
        new_img.paste(img, (x_offset, y_offset))
        return new_img

    def preprocess_image(self, image_path):
        """预处理单张图片"""
        img = Image.open(image_path).convert('L')
        img = self._center_and_resize(img)

        img_np = np.array(img, dtype=np.float32) / 255.0
        img_np = (img_np - 0.1307) / 0.3081
        img_tensor = torch.from_numpy(img_np).unsqueeze(0).unsqueeze(0)
        return img_tensor.to(self.device)

    def recognize_single(self, image_path):
        """识别单张图片"""
        start_time = time.time()
        img_tensor = self.preprocess_image(image_path)

        with torch.no_grad():
            output = self.model(img_tensor)
            probabilities = torch.exp(output)
            confidence, predicted = torch.max(probabilities, 1)

        end_time = time.time()
        inference_time = (end_time - start_time) * 1000

        result = {
            'digit': predicted.item(),
            'confidence': confidence.item() * 100,
            'inference_time': inference_time,
            'all_probabilities': probabilities[0].cpu().numpy() * 100
        }
        return result

    def recognize_batch(self, image_paths):
        """批量识别图片"""
        results = []
        for path in image_paths:
            try:
                result = self.recognize_single(path)
                result['filename'] = os.path.basename(path)
                results.append(result)
            except Exception as e:
                results.append({
                    'filename': os.path.basename(path),
                    'error': str(e)
                })
        return results
