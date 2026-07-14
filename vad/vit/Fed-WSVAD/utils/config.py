import argparse

parser = argparse.ArgumentParser()

parser.add_argument("--dataset", type=str, default="me", choices=["ucf", "xd", "me"])
parser.add_argument("--batch_size", type=int, default=64, help="batch size")
parser.add_argument("--learning_rate", type=float, default=1e-4, help="Local learning rate")
parser.add_argument("--global_rounds", type=int, default=20, help="Global federated learning rounds")
parser.add_argument("--local_epochs", type=int, default=10, help="local training epochs for each client")
parser.add_argument("--algorithm", type=str, default="FedAvg", choices=["FedAvg", "FedProx", "Scaffold"])
parser.add_argument("--clients_num", type=int, default=13, help="Number of client per round when random")
parser.add_argument("--split_mode", type=str, default="event", choices=["random", "event", "scene"])
parser.add_argument('--scheduler_rate', default=0.1)
parser.add_argument('--scheduler_milestones', default=[])
parser.add_argument('--load_model', type=int, default=0)
parser.add_argument('--checkpoint', type=str, default=None)
parser.add_argument('--cuda', type=int, default=0)

parser.add_argument('--embed_dim', default=512, type=int, help="CLIP embedding size")
parser.add_argument('--visual_length', default=256, type=int, help="length of video")
parser.add_argument('--visual_width', default=512, type=int)
parser.add_argument('--visual_head', default=1, type=int)
parser.add_argument('--visual_layers', default=2, type=int, help="number of visual layers, default 2 for ucf")

parser.add_argument('--attn_window', default=8, type=int, help="size of attention window, default 8 for ucf")
parser.add_argument('--prompt_prefix', default=10, type=int)
parser.add_argument('--prompt_postfix', default=10, type=int)

