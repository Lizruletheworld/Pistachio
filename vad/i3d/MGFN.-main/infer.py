import torch
from torch.utils.data import DataLoader
import option
from config import Config
from models.mgfn import mgfn
from datasets.dataset import Dataset
from test import test # 只需要导入 test
import os

if __name__ == '__main__':
    # 1. 加载参数 (会加载 option.py 中的所有默认值)
    args = option.parse_args()
    
    # --- (用户修改区域) ---
    # 在这里“规定死”你的参数
    
    # 1. 规定数据集名称
    args.datasetname = "UCF"  # 比如 "XD", "ShanghaiTech", "UCF" 等
    
    # 2. 规定你的模型路径
    # !! 请确保使用你自己的完整路径 !!
    args.pretrained_ckpt = "/home/intern/lijie/baseline_output/MGFN.-main/ckpt/mgfn69-i3d.pkl" 
    # ---------------------

    print(f"--- 模式: 仅测试 ---")
    print(f"已固定数据集: {args.datasetname}")
    print(f"已固定模型路径: {args.pretrained_ckpt}")

    config = Config(args)

    # 2. 设置设备
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")

    # 3. 加载测试数据
    # Dataset() 会自动使用上面固定的 args.datasetname
    test_loader = DataLoader(Dataset(args, test_mode=True),
                             batch_size=1, shuffle=False,
                             num_workers=0, pin_memory=False)

    # 4. 初始化模型
    model = mgfn()
    model = model.to(device)

    # 5. 关键：加载你训练好的模型权重
    # 检查文件是否存在
    if not os.path.exists(args.pretrained_ckpt):
        print(f"错误：找不到指定的模型文件 {args.pretrained_ckpt}")
        print("请检查 evaluate.py 脚本中的 'args.pretrained_ckpt' 路径是否正确")
        exit()

    try:
        # map_location=device 确保模型能被正确加载到当前设备
        model_ckpt = torch.load(args.pretrained_ckpt, map_location=device)
        model.load_state_dict(model_ckpt)
        print(f"\n成功从 {args.pretrained_ckpt} 加载模型权重")
    except Exception as e:
        print(f"加载模型时出错: {e}")
        exit()

    # 6. 切换到评估模式 (这很重要，会关闭 Dropout、BatchNorm 等)
    model.eval()

    # 7. 运行测试
    print("开始测试...")
    # 使用 torch.no_grad() 来节约显存并加速，因为测试时不需要计算梯度
    with torch.no_grad():
        auc, pr_auc = test(test_loader, model, args, device)

    # 8. 打印结果
    print("--- 测试完成 ---")
    print(f"数据集: {args.datasetname}")
    print(f"模型: {args.pretrained_ckpt}")
    print(f"AUC-ROC: {auc:.4f}")
    print(f"PR-AUC (AP): {pr_auc:.4f}")