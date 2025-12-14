import torch
import numpy as np
from dataset_loader import Pistachio # Assuming Pistachio class is defined elsewhere
from options import parse_args # Assuming options are defined elsewhere
from config import Config # Assuming Config class is defined elsewhere
import utils # Assuming utils functions are defined elsewhere
import os
from model import WSAD # Assuming WSAD model is defined elsewhere
from dataset_loader import data
from sklearn.metrics import precision_recall_curve, roc_curve, auc

def evaluate_model(net, config, test_loader, model_file=None):
    """
    Performs inference and segment-level evaluation for the WSAD model.
    """
    with torch.no_grad():
        net.eval()
        net.flag = "Test"
        if model_file is not None:
            # Load the model weights
            net.load_state_dict(torch.load(model_file, map_location='cuda:0'))

        load_iter = iter(test_loader)
        
        # 1. Load the Segment-Level Ground Truth file (e.g., 402 videos * 32 segments = 12864)
        # NOTE: This GT file must be segment-level, not frame-level.
        frame_gt = np.load("/home/intern/lijie/baseline_output/UR-DMU-master/list/combined_segment_gt_32.npy")
        
        # List to collect segment scores from all videos
        segment_scores_list = []
        
        print(f"Starting segment-level inference for {len(test_loader.dataset)} videos...")
        
        # Iterate over all videos (assuming batch_size=1)
        for i in range(len(test_loader.dataset)):
            _data, _label, _name = next(load_iter)
            _data = _data.cuda()
            
            # Forward pass: model outputs scores for each segment
            res = net(_data) 
            
            # res["frame"] shape is (1, num_segments), e.g., (1, 32)
            # Squeeze to get the segment scores: (num_segments,)
            segment_scores = res["frame"].squeeze().cpu().numpy()
            
            # Append the 32 segment scores of the current video to the list
            segment_scores_list.append(segment_scores)
            
        # After loop:
        # 3. Concatenate all segment score arrays into one large array
        # Final shape: (Total Videos * num_segments), e.g., (402 * 32) = 12864
        segment_predictions = np.concatenate(segment_scores_list)
        
        print(f"Inference complete. GT shape: {frame_gt.shape}, Segment Pred shape: {segment_predictions.shape}")

        # 4. Save the Segment-Level Prediction results
        np.save('frame_label/pistachio_segment_predictions.npy', segment_predictions)
        
        # 5. Calculate Segment-Level Performance Metrics (AUC and AP)
        
        # --- Calculate Segment-Level AUC ---
        fpr, tpr, _ = roc_curve(frame_gt, segment_predictions)
        auc_score = auc(fpr, tpr)
        print("Segment-Level AUC Score:", auc_score)
        
        # --- Calculate Segment-Level AP ---
        precision, recall, th = precision_recall_curve(frame_gt, segment_predictions)
        ap_score = auc(recall, precision)
        print("Segment-Level AP Score:", ap_score)


if __name__ == "__main__":
    # Parse command line arguments
    args = parse_args()
    if args.debug:
        pdb.set_trace()
    
    # Initialize Configuration
    config = Config(args)
    worker_init_fn = None
    config.len_feature = 2048
    
    # Set random seed for reproducibility
    if config.seed >= 0:
        utils.set_seed(config.seed)
        worker_init_fn = np.random.seed(config.seed)
    
    # Initialize the WSAD model
    net = WSAD(input_size=config.len_feature, flag="Test", a_nums=60, n_nums=60)
    net = net.cuda()
    
    # Initialize the Test DataLoader
    test_loader = data.DataLoader(
        Pistachio(root_dir=config.root_dir, mode='Test', modal=config.modal, 
                  num_segments=config.num_segments, len_feature=config.len_feature),
        batch_size=1, # Crucial for segment-by-segment processing
        shuffle=False, 
        num_workers=config.num_workers,
        worker_init_fn=worker_init_fn
    )
    
    # Run the evaluation function
    evaluate_model(net, config, test_loader, model_file=os.path.join(args.model_path, "me_trans_2022.pkl"))