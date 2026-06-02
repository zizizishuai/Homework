import argparse
import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import StepLR
from torchvision import datasets, transforms
from torch.utils.data import DataLoader
import matplotlib.pyplot as plt
import numpy as np
import os
from model import CNN, MLP

class Trainer:
    """模型训练器类"""
    def __init__(self, model_type='CNN', batch_size=64, lr=0.001, epochs=10,
                 augment=True, weight_decay=1e-4, scheduler_step=10, scheduler_gamma=0.5):
        self.model_type = model_type
        self.batch_size = batch_size
        self.lr = lr
        self.epochs = epochs
        self.augment = augment
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.best_test_acc = 0.0
        self.best_epoch = 0
        self.best_model_state = None
        self.weight_decay = weight_decay
        self.scheduler_step = scheduler_step
        self.scheduler_gamma = scheduler_gamma

        self.transform = self._build_transform()

        if model_type == 'CNN':
            self.model = CNN().to(self.device)
        else:
            self.model = MLP().to(self.device)

        self.criterion = nn.CrossEntropyLoss()
        self.optimizer = optim.Adam(self.model.parameters(), lr=lr, weight_decay=self.weight_decay)
        self.scheduler = StepLR(self.optimizer, step_size=self.scheduler_step, gamma=self.scheduler_gamma)

        self.train_losses = []
        self.train_accs = []
        self.test_losses = []
        self.test_accs = []

    def _build_transform(self):
        transforms_list = []
        if self.augment:
            transforms_list.extend([
                transforms.RandomRotation(10),
                transforms.RandomAffine(0, translate=(0.05, 0.05), scale=(0.9, 1.1)),
                transforms.RandomPerspective(distortion_scale=0.1, p=0.5),
            ])
        transforms_list.extend([
            transforms.ToTensor(),
            transforms.Normalize((0.1307,), (0.3081,))
        ])
        return transforms.Compose(transforms_list)

    def load_data(self):
        """加载MNIST数据集"""
        train_dataset = datasets.MNIST(
            root='./data', train=True, download=True, transform=self.transform
        )
        test_dataset = datasets.MNIST(
            root='./data', train=False, download=True, transform=transforms.Compose([
                transforms.ToTensor(),
                transforms.Normalize((0.1307,), (0.3081,))
            ])
        )

        self.train_loader = DataLoader(
            train_dataset, batch_size=self.batch_size, shuffle=True, num_workers=2, pin_memory=True
        )
        self.test_loader = DataLoader(
            test_dataset, batch_size=self.batch_size, shuffle=False, num_workers=2, pin_memory=True
        )

        print(f"训练集大小: {len(train_dataset)}, 测试集大小: {len(test_dataset)}")

    def train_epoch(self):
        """训练一个epoch"""
        self.model.train()
        running_loss = 0.0
        correct = 0
        total = 0

        for data, target in self.train_loader:
            data, target = data.to(self.device), target.to(self.device)

            self.optimizer.zero_grad()
            output = self.model(data)
            loss = self.criterion(output, target)
            loss.backward()
            self.optimizer.step()

            running_loss += loss.item()
            _, predicted = torch.max(output.data, 1)
            total += target.size(0)
            correct += (predicted == target).sum().item()

        epoch_loss = running_loss / len(self.train_loader)
        epoch_acc = 100.0 * correct / total

        self.train_losses.append(epoch_loss)
        self.train_accs.append(epoch_acc)

        return epoch_loss, epoch_acc

    def test_epoch(self):
        """测试一个epoch"""
        self.model.eval()
        test_loss = 0.0
        correct = 0
        total = 0

        with torch.no_grad():
            for data, target in self.test_loader:
                data, target = data.to(self.device), target.to(self.device)
                output = self.model(data)
                loss = self.criterion(output, target)

                test_loss += loss.item()
                _, predicted = torch.max(output.data, 1)
                total += target.size(0)
                correct += (predicted == target).sum().item()

        test_loss /= len(self.test_loader)
        test_acc = 100.0 * correct / total

        self.test_losses.append(test_loss)
        self.test_accs.append(test_acc)

        return test_loss, test_acc

    def train(self, progress_callback=None):
        """完整训练过程"""
        self.load_data()
        print(f"开始训练 {self.model_type} 模型，共 {self.epochs} 个epoch")
        print(f"使用设备: {self.device}")

        for epoch in range(1, self.epochs + 1):
            train_loss, train_acc = self.train_epoch()
            test_loss, test_acc = self.test_epoch()
            self.scheduler.step()

            print(f'Epoch {epoch}/{self.epochs}:')
            print(f'  训练损失: {train_loss:.4f}, 训练准确率: {train_acc:.2f}%')
            print(f'  测试损失: {test_loss:.4f}, 测试准确率: {test_acc:.2f}%')
            print(f'  当前学习率: {self.scheduler.get_last_lr()[0]:.6f}')

            if test_acc > self.best_test_acc:
                self.best_test_acc = test_acc
                self.best_epoch = epoch
                self.best_model_state = {k: v.cpu() for k, v in self.model.state_dict().items()}
                self.save_model('./models/mnist_model_best.pth')
                print(f'  已保存当前最佳模型: {self.best_test_acc:.2f}%')

            if progress_callback:
                progress_callback(epoch, self.epochs, train_acc, test_acc)

        if self.best_model_state is not None:
            self.model.load_state_dict(self.best_model_state)

        print('训练完成!')
        print(f'最佳测试准确率: {self.best_test_acc:.2f}% (Epoch {self.best_epoch})')
        return self.model

    def save_model(self, path='./models/mnist_model.pth'):
        """保存模型"""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'model_type': self.model_type,
            'train_losses': self.train_losses,
            'train_accs': self.train_accs,
            'test_losses': self.test_losses,
            'test_accs': self.test_accs,
            'best_test_acc': self.best_test_acc,
            'best_epoch': self.best_epoch,
        }, path)
        print(f"模型已保存到: {path}")

    def plot_training_history(self, save_path='./training_history.png'):
        """绘制训练历史曲线"""
        plt.figure(figsize=(12, 5))

        plt.subplot(1, 2, 1)
        plt.plot(self.train_losses, label='训练损失')
        plt.plot(self.test_losses, label='测试损失')
        plt.title('损失曲线')
        plt.xlabel('Epoch')
        plt.ylabel('损失')
        plt.legend()
        plt.grid(True)

        plt.subplot(1, 2, 2)
        plt.plot(self.train_accs, label='训练准确率')
        plt.plot(self.test_accs, label='测试准确率')
        plt.title('准确率曲线')
        plt.xlabel('Epoch')
        plt.ylabel('准确率 (%)')
        plt.legend()
        plt.grid(True)

        plt.tight_layout()
        plt.savefig(save_path)
        plt.close()
        print(f"训练历史图已保存到: {save_path}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Train MNIST digit recognition model')
    parser.add_argument('--model', default='CNN', choices=['CNN', 'MLP'], help='model type')
    parser.add_argument('--batch_size', type=int, default=64, help='batch size')
    parser.add_argument('--lr', type=float, default=0.001, help='learning rate')
    parser.add_argument('--epochs', type=int, default=10, help='number of epochs')
    parser.add_argument('--no_augment', action='store_true', help='disable data augmentation')
    parser.add_argument('--weight_decay', type=float, default=1e-4, help='weight decay')
    parser.add_argument('--scheduler_step', type=int, default=10, help='lr scheduler step size')
    parser.add_argument('--scheduler_gamma', type=float, default=0.5, help='lr scheduler gamma')
    args = parser.parse_args()

    trainer = Trainer(
        model_type=args.model,
        batch_size=args.batch_size,
        lr=args.lr,
        epochs=args.epochs,
        augment=not args.no_augment,
        weight_decay=args.weight_decay,
        scheduler_step=args.scheduler_step,
        scheduler_gamma=args.scheduler_gamma,
    )
    trainer.train()
    trainer.save_model()
    trainer.plot_training_history()
        