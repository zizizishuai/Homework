import argparse
import os
import torch
import torch.nn.functional as F
from torchvision import datasets, transforms
from torch.utils.data import DataLoader
from model import CNN, MLP
import numpy as np
import matplotlib.pyplot as plt


def load_model(model_path, device):
    checkpoint = torch.load(model_path, map_location=device)
    model_type = checkpoint.get('model_type', 'CNN')
    if model_type == 'CNN':
        model = CNN().to(device)
    else:
        model = MLP().to(device)
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()
    return model, model_type


def build_test_loader(batch_size):
    test_transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.1307,), (0.3081,))
    ])
    test_dataset = datasets.MNIST(root='./data', train=False, download=True, transform=test_transform)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False, num_workers=2, pin_memory=True)
    return test_loader, test_dataset


def evaluate(model, device, test_loader):
    model.eval()
    total = 0
    correct = 0
    all_preds = []
    all_labels = []

    with torch.no_grad():
        for data, target in test_loader:
            data, target = data.to(device), target.to(device)
            output = model(data)
            pred = output.argmax(dim=1, keepdim=False)
            total += target.size(0)
            correct += pred.eq(target).sum().item()
            all_preds.append(pred.cpu().numpy())
            all_labels.append(target.cpu().numpy())

    all_preds = np.concatenate(all_preds)
    all_labels = np.concatenate(all_labels)
    return correct / total * 100.0, all_preds, all_labels


def plot_confusion_matrix(labels, preds, save_path):
    num_classes = 10
    cm = np.zeros((num_classes, num_classes), dtype=int)
    for t, p in zip(labels, preds):
        cm[t, p] += 1

    plt.figure(figsize=(8, 6))
    plt.imshow(cm, interpolation='nearest', cmap=plt.cm.Blues)
    plt.title('混淆矩阵')
    plt.colorbar()
    tick_marks = np.arange(num_classes)
    plt.xticks(tick_marks, tick_marks)
    plt.yticks(tick_marks, tick_marks)
    plt.xlabel('预测标签')
    plt.ylabel('真实标签')

    thresh = cm.max() / 2.
    for i in range(num_classes):
        for j in range(num_classes):
            plt.text(j, i, format(cm[i, j], 'd'),
                     horizontalalignment='center',
                     color='white' if cm[i, j] > thresh else 'black')

    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()
    print(f'混淆矩阵已保存到: {save_path}')


def main():
    parser = argparse.ArgumentParser(description='Evaluate MNIST model performance')
    parser.add_argument('--model_path', default='./models/mnist_model_best.pth', help='Path to the saved model file')
    parser.add_argument('--batch_size', type=int, default=128, help='Evaluation batch size')
    parser.add_argument('--save_confusion', action='store_true', help='Save confusion matrix image')
    args = parser.parse_args()

    if not os.path.exists(args.model_path):
        fallback = './models/mnist_model.pth'
        if os.path.exists(fallback):
            print(f'模型文件 {args.model_path} 不存在，改为使用 {fallback}')
            args.model_path = fallback
        else:
            raise FileNotFoundError(f'未找到模型文件: {args.model_path}')

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model, model_type = load_model(args.model_path, device)
    print(f'加载模型: {args.model_path} ({model_type})')

    test_loader, _ = build_test_loader(args.batch_size)
    accuracy, preds, labels = evaluate(model, device, test_loader)
    print(f'测试集准确率: {accuracy:.2f}%')

    if args.save_confusion:
        plot_confusion_matrix(labels, preds, './evaluation_confusion.png')

if __name__ == '__main__':
    main()
