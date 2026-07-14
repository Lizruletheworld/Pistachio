import os
import random
import numpy as np
import torch
import utils.config as config
from fed.server import FedAvgServer
from utils.dataset import make_xd_dataloader, make_ucf_dataloader, make_me_dataloader
from utils.model import Model
from datetime import datetime


def setup_seed(seed):
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    np.random.seed(seed)
    random.seed(seed)
    # torch.backends.cudnn.deterministic = True


if __name__ == "__main__":
    setup_seed(88888888)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    args = config.parser.parse_args()
    device = f"cuda:{args.cuda}" if torch.cuda.is_available() else "cpu"

    start_time = datetime.now()
    dir_name = start_time.strftime("%Y-%m-%d-%H:%M:%S")
    dir_name = args.dataset + "-" + dir_name
    path = os.path.join('save', dir_name)
    os.mkdir(path)

    with open(os.path.join(path, 'README.txt'), 'w') as f:
        for key, value in args.__dict__.items():
            print(f'{key}: {value}', file=f)

    train_loaders = []

    if args.dataset == "xd":
        train_loaders, test_loader = make_xd_dataloader(
            args.split_mode, args.clients_num, args.batch_size, args.visual_length)

    elif args.dataset == "me":
        train_loaders, test_loader = make_me_dataloader(
            args.split_mode, args.clients_num, args.batch_size, args.visual_length)

    else:
        train_loaders, test_loader = make_ucf_dataloader(
            args.split_mode, args.clients_num, args.batch_size, args.visual_length)

    model = Model(args.embed_dim, args.visual_length, args.prompt_prefix,
                  args.prompt_postfix, args.visual_width, args.visual_layers,
                  args.visual_head, args.attn_window, device).to(device)

    if args.load_model == 1:
        checkpoint = torch.load(args.checkpoint)

        model.load_state_dict(checkpoint)

    if args.algorithm == "FedAvg":
        server = FedAvgServer(args.dataset, train_loaders, test_loader, args.clients_num,
                              args.global_rounds, args.local_epochs, args.learning_rate,
                              args.split_mode, args.scheduler_milestones, args.scheduler_rate,
                              device, model)
        server.train(path)

