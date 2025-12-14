# import torch
# from options import *
# from config import *
# from model import *
# import numpy as np
# from dataset_loader import *
# from sklearn.metrics import roc_curve,auc,precision_recall_curve
# import warnings
# warnings.filterwarnings("ignore")

# def test(net, config, wind, test_loader, test_info, step, model_file = None):
#     with torch.no_grad():
#         net.eval()
#         net.flag = "Test"
#         if model_file is not None:
#             net.load_state_dict(torch.load(model_file))

#         load_iter = iter(test_loader)
#         frame_gt = np.load("/home/intern/lijie/Wan2.2/benchmark_test_last_gt/combined_segment_gt_eval_16x.npy")
#         frame_predict = None
        
#         cls_label = []
#         cls_pre = []
#         temp_predict = torch.zeros((0)).cuda()
        
#         for i in range(len(test_loader.dataset)):
            
#             _data, _label,_ = next(load_iter)
            
#             _data = _data.cuda()
#             _label = _label.cuda()
            
#             res = net(_data)   
#             a_predict = res["frame"]
#             temp_predict = torch.cat([temp_predict, a_predict], dim=0)
#             if (i + 1) % 10 == 0 :
#                 cls_label.append(int(_label))
#                 a_predict = temp_predict.mean(0).cpu().numpy()
                
#                 cls_pre.append(1 if a_predict.max()>0.5 else 0)          
#                 fpre_ = np.repeat(a_predict, 16)
#                 if frame_predict is None:         
#                     frame_predict = fpre_
#                 else:
#                     frame_predict = np.concatenate([frame_predict, fpre_])  
#                 temp_predict = torch.zeros((0)).cuda()
   
#         fpr,tpr,_ = roc_curve(frame_gt, frame_predict)
#         auc_score = auc(fpr, tpr)
    
#         corrent_num = np.sum(np.array(cls_label) == np.array(cls_pre), axis=0)
#         accuracy = corrent_num / (len(cls_pre))
        
#         precision, recall, th = precision_recall_curve(frame_gt, frame_predict,)
#         ap_score = auc(recall, precision)

#         wind.plot_lines('roc_auc', auc_score)
#         wind.plot_lines('accuracy', accuracy)
#         wind.plot_lines('pr_auc', ap_score)
#         wind.lines('scores', frame_predict)
#         wind.lines('roc_curve',tpr,fpr)
#         test_info["step"].append(step)
#         test_info["auc"].append(auc_score)
#         test_info["ap"].append(ap_score)
#         test_info["ac"].append(accuracy)
import torch
from options import *
from config import *
from model import *
import numpy as np
from dataset_loader import *
from sklearn.metrics import roc_curve,auc,precision_recall_curve
import warnings
warnings.filterwarnings("ignore")

def test(net, config, wind, test_loader, test_info, step, model_file = None):
    with torch.no_grad():
        net.eval()
        net.flag = "Test"
        if model_file is not None:
            net.load_state_dict(torch.load(model_file))

        load_iter = iter(test_loader)
        
        # 1. 【【修改】】加载你的 "不上采样" GT 文件
        # ！！！请确保这个文件的长度是 8230 ！！！
        gt_file_path = "/home/intern/lijie/Wan2.2/benchmark_test_last_gt/combined_segment_gt_402_32seg.npy" # <-- 替换成你的路径
        try:
            frame_gt = np.load(gt_file_path)
        except FileNotFoundError:
            print(f"CRITICAL ERROR: 找不到GT文件: {gt_file_path}")
            return
            
        # 2. 使用一个列表来高效收集预测值
        frame_predict_list = []
        
        # ----------------------------------------------------
        # 这部分是用于视频级分类的，保持不变
        cls_label = []
        cls_pre = []
        temp_predict = torch.zeros((0)).cuda()
        # ----------------------------------------------------

        print(f"Starting test loop for {len(test_loader.dataset)} videos...")
        print(f"Expecting {len(frame_gt)} total segments from GT file.")

        for i in range(len(test_loader.dataset)):
            
            _data, _label,_ = next(load_iter)
            _data = _data.cuda()
            _label = _label.cuda()
            
            res = net(_data)
            
            # a_predict_segments 是这个 *单个视频* 的 *片段* 预测
            # 假设 res["frame"] shape 是 (1, num_segments) 或 (num_segments,)
            a_predict_segments = res["frame"].squeeze().cpu().numpy()

            # 3. 【【修改】】直接添加片段预测， *不* 需要 np.repeat
            frame_predict_list.append(a_predict_segments)

            # ----------------------------------------------------
            # 视频级分类逻辑 (保持不变)
            temp_predict = torch.cat([temp_predict, res["frame"].squeeze(0)], dim=0) 
            
            if (i + 1) % 10 == 0 :
                cls_label.append(int(_label))
                a_predict_for_cls = temp_predict.mean(0).cpu().numpy()
                cls_pre.append(1 if a_predict_for_cls.max() > 0.5 else 0) 
                temp_predict = torch.zeros((0)).cuda()
            # ----------------------------------------------------

        # --- 循环结束后 ---
        
        # 4. 【【修改】】合并所有 *片段* 预测
        frame_predict = np.concatenate(frame_predict_list)

        # 5. 【【重要】】检查 GT 和 预测的长度是否匹配
        print(f"Final GT length: {len(frame_gt)}, Final Predict length: {len(frame_predict)}")
        if len(frame_gt) != len(frame_predict):
            print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            print("CRITICAL WARNING: GT 和 Prediction 长度不匹配!")
            print(f"GT: {len(frame_gt)}, Pred: {len(frame_predict)}")
            print("ROC/AUC 计算将会失败。请检查你的GT文件是否与测试集片段总数完全对应。")
            print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            
            # 紧急处理：裁剪到最短长度
            min_len = min(len(frame_gt), len(frame_predict))
            frame_gt = frame_gt[:min_len]
            frame_predict = frame_predict[:min_len]
            print(f"已将两者裁剪到最小长度: {min_len}")
    
        # 6. 现在两个数组长度一致 (都应该是 8230)，可以计算 ROC
        fpr,tpr,_ = roc_curve(frame_gt, frame_predict)
        auc_score = auc(fpr, tpr)
    
        corrent_num = np.sum(np.array(cls_label) == np.array(cls_pre), axis=0)
        accuracy = corrent_num / (len(cls_pre))
        
        precision, recall, th = precision_recall_curve(frame_gt, frame_predict,)
        ap_score = auc(recall, precision)

        wind.plot_lines('roc_auc', auc_score)
        wind.plot_lines('accuracy', accuracy)
        wind.plot_lines('pr_auc', ap_score)
        wind.lines('scores', frame_predict)
        wind.lines('roc_curve',tpr,fpr)
        test_info["step"].append(step)
        test_info["auc"].append(auc_score)
        test_info["ap"].append(ap_score)
        test_info["ac"].append(accuracy)