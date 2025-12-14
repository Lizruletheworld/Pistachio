"""
Multi-Scale Unsupervised Learning of Density Estimates (MULDE) for Anomaly Detection.

Usage Examples:
# Training without regularization
python main.py

# Training with regularization beta=0.1 and L=16 noise levels for evaluation
python main.py --beta 0.1 --L 16

# Training an MLP with layer normalization and dropout
python main.py --layernorm --dropout 0.5

# Plot the training/testing data distribution before training starts
python main.py --plot_dataset

# Launch TensorBoard to visualize training metrics and plots
tensorboard --logdir=runs/MULDE --samples_per_plugin images=100

Evaluation Note:
We distinguish between individual sigma evaluation and an aggregate evaluation.
- An aggregate is either based on the AUC-ROC of Gaussian Mixture Models (GMMs) or a max/median/mean of the standardized scores across all sigmas 1:L.
- The individual sigma evaluation is based on the AUC-ROC of the scores for each individual sigma from 1 to L.
"""

import numpy as np
import argparse
import utils
import torch
from models import MLPs, ScoreOrLogDensityNetwork
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader
from sklearn.metrics import roc_auc_score
from tqdm import tqdm
from sklearn import mixture
import matplotlib.pyplot as plt
# from dataset import get_dataset, create_meshgrid_from_data
from my_dataset_loader import get_dataset, create_meshgrid_from_data
torch.cuda.empty_cache()
import plotting_utils

figsize = (7, 7)
edgecolors = None
linewidths = 1.
marker = "x"
cmap_mesh = "viridis" # "coolwarm"


def train_and_evaluate(args):
    
    # --- 1. SET YOUR DATA PATH HERE ---
    # This directory must contain the preprocessed features (from your preprocess.py script)
    data_dir = "/home/intern/lijie/baseline/MULDE/preprocessed_for_MULDE" # Example Path
    m_file_path = "" # Not used here, but required by the dataset loader
    
    # --- 2. Load Dataset ---
    # zeros are normal (ID), ones are anomalous (OOD)
    data_train, labels_train, data_test, labels_test, id_to_type = get_dataset(data_dir, m_file_path)

    data_train = torch.Tensor(data_train)
    data_test = torch.Tensor(data_test)

    # --- Data Standardization ---
    data_train_mean = torch.Tensor(np.asarray([0.]))
    data_train_std = torch.Tensor(np.asarray([1.]))
    if not args.unstandardized:
        # stats component-wise
        data_train_mean = data_train.mean(dim=0)
        data_train_std = data_train.std(dim=0)

    data_train_mean = data_train_mean.to(args.device)
    data_train_std = data_train_std.to(args.device)

    # --- Data Loaders ---
    dataset_train = TensorDataset(data_train, torch.Tensor(labels_train))
    dataset_test = TensorDataset(data_test, torch.Tensor(labels_test))
    dataloader_train = DataLoader(dataset_train, shuffle=True, batch_size=args.batch_size)
    dataloader_test = DataLoader(dataset_test, shuffle=False, batch_size=args.batch_size)

    # --- Manifold Data Loader for 2D Plotting ---
    if data_train.shape[1] == 2:
        meshgrid_points = 200
        xx, yy = create_meshgrid_from_data(np.vstack([data_train, data_test]), n_points=meshgrid_points, meshgrid_offset=args.meshgrid_offset)
        data_manifold = np.hstack([xx.reshape(-1, 1), yy.reshape(-1, 1)])

        # xx and yy are manifold points
        dataset_manifold = TensorDataset(torch.Tensor(data_manifold), torch.Tensor(np.asarray([0] * len(data_manifold))))
        dataloader_manifold = DataLoader(dataset_manifold, shuffle=False, batch_size=args.batch_size)


    # --- Model Initialization ---
    input_dim = data_train.reshape(data_train.shape[0], -1).shape[1]
    model = ScoreOrLogDensityNetwork(MLPs(input_dim=input_dim + 1, # +1 for noise conditioning
                                         units=args.units,
                                         dropout=args.dropout,
                                         layernorm=args.layernorm),
                                  score_network=False) 

    # --- Multi-GPU Support ---
    if torch.cuda.device_count() > 1:
        print(f"Detected {torch.cuda.device_count()} GPUs. Using DataParallel.")
        # DataParallel automatically distributes batch data across all *visible* GPUs
        model = torch.nn.DataParallel(model) 
    
    # Move model (main copy) to the target device
    model = model.to(args.device)

    # --- Gradient Clipping ---
    if args.gradient_clipping:
        clip_value = args.gradient_clipping 
        for p in model.parameters():
            p.register_hook(lambda grad: torch.clamp(grad, -clip_value, clip_value))

    optimizer = optim.Adam(model.parameters(), lr=args.lr, betas=(0.5, 0.9))

    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=50, gamma=0.9)
    
    # --- Logging Setup ---
    log_path, summary_writer = utils.get_log_path_and_summary_writer(root_dir_runs="runs",
                                                                     experiment_name=args.experiment_name,
                                                                     args=args)
    utils.save_current_experiment_source_code(log_path)

    # --- Initial Dataset Plotting ---
    if args.plot_dataset and data_train.shape[1] == 2:
        plt.figure(figsize=figsize)
        plt.scatter(data_train[:, 0], data_train[:, 1], c='blue', marker=marker, label='train', edgecolors=edgecolors, linewidths=linewidths)
        data_test_id = data_test[labels_test == 0]
        data_test_ood = data_test[labels_test == 1]
        plt.scatter(data_test_id[:, 0], data_test_id[:, 1], c='green', marker=marker, label='test ID', edgecolors=edgecolors, linewidths=linewidths)
        plt.scatter(data_test_ood[:, 0], data_test_ood[:, 1], c='red', marker=marker, label='test OOD', edgecolors=edgecolors, linewidths=linewidths)

        plt.gca().set_aspect('equal', adjustable='box')
        plt.legend()

        summary_writer.add_figure(f"dataset", plt.gcf(), 0)
        plt.close()


    # ================================================================================================================
    # Training Loop
    # ================================================================================================================
    for epoch in range(args.epochs + 1):
        # ################################################################################################################
        # train step
        # ################################################################################################################
        with tqdm(dataloader_train) as tepoch:
            tepoch.set_description(f"Train Epoch {epoch}")
            model.train()
            loss_accumulate = 0
            loss_accumulate_train = utils.LossAccumulate()

            for batch_idx, data in enumerate(tepoch):
                x = data[0].to(args.device)
                x = x.reshape(x.shape[0], -1)
                x = (x - data_train_mean) / (data_train_std + 1e-8)

                # ###########
                # sample sigma
                sigma = torch.Tensor(np.exp(np.random.uniform(np.log(args.sigma_low), np.log(args.sigma_high), x.size(0)))).unsqueeze(1).to(args.device)

                # sample noise
                noise = torch.randn_like(x, device=args.device) * sigma 

                x = x.requires_grad_()
                x_ = x + noise # add noise to data

                lambda_factor = (sigma ** 2).ravel()
                
                # Get model.module if DataParallel is used
                model_to_call = model.module if isinstance(model, torch.nn.DataParallel) else model
                score_, log_density_ = model_to_call.score(torch.hstack([x_, sigma]), return_log_density=True) 
                
                # Denosing Score Matching (DSM) Loss
                # The score of the perturbed distribution p_sigma is estimated by the network
                # Target score: -(x - x_) / sigma^2 = -noise / sigma^2
                loss = torch.norm(score_[:, :-1] + noise / (sigma ** 2), dim=-1) ** 2 

                loss = lambda_factor.ravel() * loss
                loss = loss.mean() / 2.
                loss_accumulate_train["loss_dsm"].append(loss.item())

                # tracking metrics
                score_squared_norms = (torch.norm(score_[:, :-1], dim=1) ** 2)
                loss_accumulate_train["score_norm"] += (lambda_factor * score_squared_norms).tolist()
                loss_accumulate_train["log_density"] += log_density_.ravel().tolist()

                # --- Regularization Term ---
                loss_regularizer = torch.Tensor(np.asarray([0.])).to(args.device)
                if args.beta:
                    # Calculate log density for clean data for regularization
                    _, log_density_noise_free = model_to_call.score(torch.hstack([x, sigma]), return_log_density=True)
                    loss_regularizer = args.beta * (log_density_noise_free ** 2).mean() / 2.
                    loss += loss_regularizer

                loss_accumulate_train["loss_regularizer"].append(loss_regularizer.item())
                loss_accumulate_train["loss_dsm_reg"].append(loss.item())

                optimizer.zero_grad()
                loss.backward()

                # Track gradients
                all_grads = [torch.max(param.grad).item() for param in model.parameters() if param.grad is not None]
                if all_grads:
                    summary_writer.add_scalar(f'gradients/max_gradient', max(all_grads), epoch * len(tepoch) + batch_idx)
                
                optimizer.step()
                loss_accumulate += loss.item()

            # Log accumulated training losses and values
            for k, noise in loss_accumulate_train.items():
                loss_accumulate_train[k] = np.asarray(noise).mean()
                if "loss" in k:
                    summary_writer.add_scalar(f'loss_train/{k}', np.asarray(noise).mean(), epoch)
                else:
                    summary_writer.add_scalar(f'values_train/{k}', np.asarray(noise).mean(), epoch)

            if args.use_scheduler:
                scheduler.step()

        # ################################################################################################################
        # evaluate step
        # ################################################################################################################
        def calculate_scores(dataloader, return_scores_by_sigma=True, L=args.L):
            """
            Calculates log densities and score norms for the given dataloader across noise levels.
            :param L: int or list of floats. Number of sigmas or list of sigmas to evaluate.
            """
            with tqdm(dataloader) as tepoch:
                tepoch.set_description(f"Calculate noise-free log-densities/score norms across sigmas")
                model.eval()
                anomaly_scores = dict()
                scores_by_sigma = dict()
                loss_accumulate = dict()
                
                # Determine sigmas to evaluate
                if isinstance(L, list):
                    sigma_L = np.asarray(L).tolist()
                else:
                    sigma_L = np.linspace(args.sigma_low, args.sigma_high, L).tolist()
                    
                sigma_L = list(map(lambda x: float(f"{x:.5f}"), sigma_L))
                model_to_call = model.module if isinstance(model, torch.nn.DataParallel) else model

                for sigma_ in sigma_L:
                    score_id, log_density_id = f"score_norm_{sigma_}", f"log_density_{sigma_}"
                    if log_density_id not in anomaly_scores:
                        anomaly_scores[score_id] = list()
                        anomaly_scores[log_density_id] = list()
                        scores_by_sigma[sigma_] = {"log_density": list(), "score_norm": list()}
                        loss_accumulate[score_id] = list()
                        loss_accumulate[log_density_id] = list()

                for batch_idx, (data, labels) in enumerate(tepoch):
                    x = data.to(args.device)
                    x = x.reshape(x.shape[0], -1)
                    x = (x - data_train_mean) / (data_train_std + 1e-8)
                    x = x.requires_grad_()

                    with torch.no_grad(): # Disable gradient calculation for evaluation
                        for sigma_ in sigma_L: 
                            score_id, log_density_id = f"score_norm_{sigma_}", f"log_density_{sigma_}" 

                            # Get score and log density for the clean sample (x) at noise scale sigma_
                            lambda_factor = sigma_ ** 2 
                            sigma_tensor = sigma_ * torch.ones((x.shape[0], 1), device=x.device)
                            score_, log_density_ = model_to_call.score(torch.hstack([x, sigma_tensor]), return_log_density=True)
                            
                            score_squared_norms = (torch.norm(score_[:, :-1], dim=1) ** 2)
                            
                            anomaly_scores[log_density_id] += log_density_.ravel().tolist()
                            anomaly_scores[score_id] += (lambda_factor * score_squared_norms).ravel().tolist()

                            scores_by_sigma[sigma_]["log_density"] += log_density_.ravel().tolist()
                            scores_by_sigma[sigma_]["score_norm"] += score_squared_norms.ravel().tolist()

                if return_scores_by_sigma:
                    anomaly_scores = scores_by_sigma
                return anomaly_scores

            
        if epoch % 5 == 0:
            # Anomaly scores from test set
            scores_test = calculate_scores(dataloader_test, return_scores_by_sigma=True)

            # ############################################################################################################
            # AGGREGATE evaluation
            # ############################################################################################################
            # Anomaly scores from train set, used for calculating statistics and for GMM fitting
            scores_train = calculate_scores(dataloader_train, return_scores_by_sigma=True)

            anomaly_score_names = list(scores_train.values())[0].keys() 
            test_sigmas = list(sorted(scores_train.keys())) 

            # Calculate statistics for max, median, mean of standardized scores
            auc_roc_aggregate = dict()
            for score_type_ in anomaly_score_names:
                # L-dimensional feature vectors (L is the number of sigmas)
                multiscale_data_train_ = np.asarray([scores_train[sigma_][score_type_] for sigma_ in test_sigmas]).T
                multiscale_data_test_ = np.asarray([scores_test[sigma_][score_type_] for sigma_ in test_sigmas]).T

                # Compute mean and std from the train set
                ms_mean = multiscale_data_train_.mean(axis=0)
                ms_std = multiscale_data_train_.std(axis=0)

                # Standardize the test set features
                multiscale_data_test_standardized = (multiscale_data_test_ - ms_mean) / (ms_std + 1e-8)

                auc_roc_aggregate[f"{score_type_}"] = dict()
                
                # Max, Median, Mean aggregation
                auc_roc_aggregate[f"{score_type_}"]["max"] = roc_auc_score(labels_test, multiscale_data_test_standardized.max(axis=1))
                auc_roc_aggregate[f"{score_type_}"]["median"] = roc_auc_score(labels_test, np.median(multiscale_data_test_standardized, axis=1))
                auc_roc_aggregate[f"{score_type_}"]["mean"] = roc_auc_score(labels_test, multiscale_data_test_standardized.mean(axis=1))

                # GMM fit (if enabled)
                if args.gmm:
                    for components_ in [1, 3, 5]:
                        # fit L-dimensional TRAIN feature vectors with GMM
                        gmm = mixture.GaussianMixture(n_components=components_, covariance_type='full').fit(multiscale_data_train_)
                        # evaluate L-dimensional TEST feature vectors (GMM Log Likelihood)
                        ll_scores = gmm.score_samples(multiscale_data_test_)
                        # Add Negative Log Likelihood (NLL) of GMM to final scores (NLL is typically a good anomaly score)
                        auc_roc_aggregate[f"{score_type_}"][f"gmm({components_})_nll"] = roc_auc_score(labels_test, -ll_scores)

            # Log Aggregate results to TensorBoard
            for score_type_ in anomaly_score_names:
                best_auc_aggregate = -np.inf
                for agg_type_ in auc_roc_aggregate[score_type_].keys():
                    current_auc = auc_roc_aggregate[score_type_][agg_type_]
                    if best_auc_aggregate < current_auc:
                        best_auc_aggregate = current_auc
                    summary_writer.add_scalar(f"roc_auc_{score_type_}_aggregate/{agg_type_}", current_auc, epoch)

                summary_writer.add_scalar(f"_roc_auc_best/_best_{score_type_}_aggregate", best_auc_aggregate, epoch)

            # Bar plot comparison
            fig, ax = plt.subplots(figsize=figsize)
            categories = list(auc_roc_aggregate['log_density'].keys())
            log_density_values = list(auc_roc_aggregate['log_density'].values())
            score_norm_values = list(auc_roc_aggregate['score_norm'].values())
            bar_width = 0.35
            index = np.arange(len(categories))
            ax.bar(index, log_density_values, bar_width, label='log_density')
            ax.bar(index + bar_width, score_norm_values, bar_width, label='score_norm')
            ax.set_xlabel('Aggregation Method')
            ax.set_ylabel('AUC-ROC')
            ax.set_title('Aggregate Score Comparison')
            ax.set_xticks(index + bar_width / 2)
            ax.set_xticklabels(categories, rotation=45, ha="right")
            ax.legend()
            plt.tight_layout()
            summary_writer.add_figure(f"_roc_auc_aggregate", fig, epoch)
            plt.close()

            # ############################################################################################################
            # INDIVIDUAL sigma evaluation
            # ############################################################################################################
            best_auc_roc_log_density = 0
            best_sigma_log_density = 0
            best_auc_roc_score_norm = 0
            best_sigma_score_norm = 0
            all_auc_roc_log_density = list()
            all_auc_roc_score_norm = list()
            
            for sigma in list(sorted(scores_test.keys())):
                score_norms_ = np.asarray(scores_test[sigma]["score_norm"])
                log_densities = np.asarray(scores_test[sigma]["log_density"])

                auc_roc_log_density = roc_auc_score(labels_test, log_densities)
                auc_roc_score_norm = roc_auc_score(labels_test, score_norms_)

                all_auc_roc_log_density.append(auc_roc_log_density)
                all_auc_roc_score_norm.append(auc_roc_score_norm)

                if auc_roc_log_density > best_auc_roc_log_density:
                    best_auc_roc_log_density = auc_roc_log_density
                    best_sigma_log_density = sigma
                if auc_roc_score_norm > best_auc_roc_score_norm:
                    best_auc_roc_score_norm = auc_roc_score_norm
                    best_sigma_score_norm = sigma

                summary_writer.add_scalar(f"roc_auc_log_density_individual/sigma_{sigma}", auc_roc_log_density, epoch)
                summary_writer.add_scalar(f"roc_auc_score_norm_individual/sigma_{sigma}", auc_roc_score_norm, epoch)

            summary_writer.add_scalar(f"_roc_auc_best/_best_log_density_individual", best_auc_roc_log_density, epoch)
            summary_writer.add_scalar(f"_roc_auc_best/_best_score_norm_individual", best_auc_roc_score_norm, epoch)

            # Line plot of AUC vs. Sigma
            fig, ax = plt.subplots(figsize=figsize)
            ax.plot(list(sorted(scores_test.keys())), all_auc_roc_log_density, label="Log Density")
            ax.plot(list(sorted(scores_test.keys())), all_auc_roc_score_norm, label="Score Norm")
            ax.legend()
            ax.set_xlabel("Sigma ($\sigma$)")
            ax.set_ylabel("AUC-ROC")
            ax.set_title("AUC-ROC vs. Noise Scale ($\sigma$)")
            ax.set_xlim([list(sorted(scores_test.keys()))[0], list(sorted(scores_test.keys()))[-1]])
            ax.set_ylim([0, 1])
            summary_writer.add_figure(f"_roc_auc_individual", fig, epoch)
            plt.close()

            # --- 2D Manifold Plotting (if data dimension is 2) ---
            if args.plot_dataset and data_train.shape[1] == 2:
                # Evaluate on a few fixed sigmas for visualization
                fixed_sigmas = [1e-3, 1e-2, 1e-1, 0.5, 1.]
                scores_manifold = calculate_scores(dataloader_manifold, return_scores_by_sigma=True, L=fixed_sigmas)
                
                for sigma_, scores_ in scores_manifold.items():
                    for score_type, data_ in scores_.items():
                        # Plot score map without scatter data
                        plt.figure(figsize=figsize)
                        data_ = np.asarray(data_).reshape(meshgrid_points, meshgrid_points)
                        plotting_utils.plot_mesh(plt, xx, yy, data_, cmap=cmap_mesh, colorbar_label=f"{score_type} Score")
                        plt.title(f"{score_type} Map at $\sigma={sigma_}$")
                        summary_writer.add_figure(f"{score_type}_map/sigma_{sigma_}", plt.gcf(), epoch)
                        plt.close()

                        # Plot score map with scatter data
                        plt.figure(figsize=figsize)
                        plotting_utils.plot_mesh(plt, xx, yy, data_, cmap=cmap_mesh, colorbar_label=f"{score_type} Score")

                        # Add scatter data for visualization
                        alpha = 0.1
                        data_test_id = data_test[labels_test == 0]
                        data_test_ood = data_test[labels_test == 1]
                        plt.scatter(data_test_id[:, 0], data_test_id[:, 1], c='green', marker=marker, label='Test ID', edgecolors=edgecolors, linewidths=linewidths, alpha=alpha)
                        plt.scatter(data_test_ood[:, 0], data_test_ood[:, 1], c='red', marker=marker, label='Test OOD', edgecolors=edgecolors, linewidths=linewidths, alpha=alpha)
                        plt.gca().set_aspect('equal', adjustable='box')
                        plt.title(f"{score_type} Map with Data at $\sigma={sigma_}$")
                        plt.legend()
                        summary_writer.add_figure(f"{score_type}_map_with_data/sigma_{sigma_}", plt.gcf(), epoch)
                        plt.close()
            
            
            # --- Periodic Checkpoint Saving ---
            if epoch > 0: 
                # Check if DataParallel is used, if so, access .module for the original model state
                model_state = model.module.state_dict() if isinstance(model, torch.nn.DataParallel) else model.state_dict()

                model_save_path = f"{log_path}/model_epoch_{epoch}.pth"
                print(f"\n--- Saving checkpoint to {model_save_path} ---\n")
                torch.save(model_state, model_save_path)
            # --- Periodic Checkpoint Saving End ---


    summary_writer.flush()

    # --- Save Final Model ---
    print("Training complete. Saving final model.")
    model_state = model.module.state_dict() if isinstance(model, torch.nn.DataParallel) else model.state_dict()
    torch.save(model_state, f"{log_path}/model_final.pth")
    # --- Final Model Save End ---


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Multi-Scale Unsupervised Learning of Density Estimates (MULDE)")
    parser.add_argument("--experiment_name", type=str, default="MULDE", help="Name for the TensorBoard experiment directory.")
    parser.add_argument("--device", type=str, default="cuda:6", help="Device to use for training (e.g., cuda:0 or cpu).")
    parser.add_argument("--epochs", type=int, default=1000, help="Number of training epochs.")
    parser.add_argument("--lr", type=float, default=5e-4, help="Learning rate for the Adam optimizer.")
    parser.add_argument("--batch_size", type=int, default=2048, help="Batch size for training and evaluation.")
    parser.add_argument('--units', nargs='+', default=[4096, 4096], help='Hidden units for the MLP network.', type=int)
    parser.add_argument('--sigma_low', type=float, default=1e-3, help="Lower bound for noise scale (sigma) sampling.")
    parser.add_argument('--sigma_high', type=float, default=1., help="Upper bound for noise scale (sigma) sampling.")
    parser.add_argument('--plot_dataset', action='store_true', help="Plot the initial dataset distribution (only for 2D data).")
    parser.set_defaults(plot_dataset=False)
    parser.add_argument('--unstandardized', action='store_true', help="Do NOT standardize input data (usually keep False).")
    parser.set_defaults(unstandardized=False)
    parser.add_argument('--dropout', type=float, default=None, help="Dropout rate in the MLP.")
    parser.add_argument('--use_scheduler', action='store_true', help="Use learning rate scheduler.")
    parser.set_defaults(use_scheduler=False)
    parser.add_argument('--layernorm', action='store_true', help="Use Layer Normalization in the MLP.")
    parser.set_defaults(layernorm=False)
    parser.add_argument('--gmm', action='store_true', help="Fit GMM to log-density scores for aggregate evaluation (computationally intensive).")
    parser.set_defaults(gmm=False)
    parser.add_argument('--gradient_clipping', type=float, default=None, help='Value for gradient clipping (e.g., 5e-1).')
    parser.add_argument("--meshgrid_offset", type=float, default=10., help='Offset size for generating the 2D visualization meshgrid.')
    parser.add_argument("--L", type=int, default=16, help='Number of sigmas to evaluate for multiscale scoring.')
    parser.add_argument('--beta', type=float, default=None, help="Regularization factor for log-density squared (e.g., 0.1).")

    args = parser.parse_args()
    train_and_evaluate(args)