
import numpy as np
import torch
from sklearn.metrics import average_precision_score, roc_auc_score
from torch.utils.data import DataLoader

from utils import config
from utils.dataset import MEDataset, XDDataset, UCFDataset
from utils.model import Model
from utils.tools import get_prompt_text


def inference(dataset, model, test_loader, gt, device):
    visual_length = 256
    model.eval()
    model.to(device)
    if dataset == 'ucf':
        label_map = dict(
            {'Normal': 'normal', 'Abuse': 'abuse', 'Arrest': 'arrest', 'Arson': 'arson', 'Assault': 'assault',
             'Burglary': 'burglary', 'Explosion': 'explosion', 'Fighting': 'fighting',
             'RoadAccidents': 'roadAccidents', 'Robbery': 'robbery', 'Shooting': 'shooting',
             'Shoplifting': 'shoplifting', 'Stealing': 'stealing', 'Vandalism': 'vandalism'})
    elif dataset == 'me':
        label_map = dict({
            'Normal': 'normal',
            'animal_abuse': 'animal abuse',
            'animal_attack_or_fight': 'animal attack or fight',
            'animal_fall_and_injury': 'animal fall and injury',
            'animal_fight': 'animal fight',
            'animal_predation': 'animal predation',
            'avalanche': 'avalanche',
            'construction_accident': 'construction accident',
            'equipment_breakdown': 'equipment breakdown',
            'explosion': 'explosion',
            'extreme_weather_events': 'extreme weather events',
            'falling_object_and_collapse': 'falling object and collapse',
            'fighting_and_physical_conflict': 'fighting and physical conflict',
            'fire': 'fire',
            'ground_collapse': 'ground collapse',
            'infrastructure_failure': 'infrastructure failure',
            'landslide': 'landslide',
            'leakage': 'leakage',
            'medical_emergency': 'medical emergency',
            'natural_disasters': 'natural disasters',
            'person_drowning': 'person drowning',
            'pushing_conflict': 'pushing conflict',
            'robbery': 'robbery',
            'safety_violations': 'safety violations',
            'slip_and_fall_accident': 'slip and fall accident',
            'structural_failure': 'structural failure',
            'sudden_illness_and_seizure': 'sudden illness and seizure',
            'sudden_illness_seizure': 'sudden illness seizure',
            'theft': 'theft',
            'traffic_accident': 'traffic accident',
            'vandalism': 'vandalism',
            'weapons_incident': 'weapons incident',
            'wild_large_animal_intrusion': 'wild large animal intrusion'})
    else:
        label_map = dict({'A': 'normal', 'B1': 'fighting', 'B2': 'shooting', 'B4': 'riot',
                          'B5': 'abuse', 'B6': 'car accident', 'G': 'explosion'})

    prompt_text = get_prompt_text(label_map)
    with torch.no_grad():
        max_len = 256
        for i, item in enumerate(test_loader):

            visual = item[0].squeeze(0)
            visual = visual.to(device)
            length = item[2]

            length = int(length)
            len_cur = length
            if len_cur < visual_length:
                visual = visual.unsqueeze(0)

            lengths = torch.zeros(int(length / max_len) + 1)

            for j in range(int(length / max_len) + 1):
                if j == 0 and length < max_len:
                    lengths[j] = length
                elif j == 0 and length > max_len:
                    lengths[j] = max_len
                    length -= max_len
                elif length > max_len:
                    lengths[j] = max_len
                    length -= max_len
                else:
                    lengths[j] = length
            lengths = lengths.to(int)

            logits2 = model(visual, prompt_text, lengths)

            logits2 = logits2.reshape(logits2.shape[0] * logits2.shape[1], logits2.shape[2])
            prob2 = (1 - logits2[0:len_cur].softmax(dim=-1)[:, 0].squeeze(-1))

            if i == 0:
                ap2 = prob2
            else:
                ap2 = torch.cat([ap2, prob2], dim=0)

    ap2 = ap2.cpu().numpy()
    ap2 = ap2.tolist()
    ROC2 = roc_auc_score(gt, np.repeat(ap2, 16))
    AP2 = average_precision_score(gt, np.repeat(ap2, 16))

    return ROC2, AP2


if __name__ == "__main__":
    args = config.parser.parse_args()

    if args.dataset == 'ucf':
        test_list = './data/list/ucf_test.csv'
        test_dataset = UCFDataset(args.visual_length, test_list, True)
    elif args.dataset == 'me':
        test_list = './data/list/me_test.csv'
        test_dataset = MEDataset(args.visual_length, test_list, True)

    else:
        test_list = './data/list/xd_test.csv'
        test_dataset = XDDataset(args.visual_length, test_list, True)

    test_loader = DataLoader(test_dataset, batch_size=1, shuffle=False)
    device = "cuda:0" if torch.cuda.is_available() else "cpu"

    model = Model(args.embed_dim, args.visual_length, args.prompt_prefix,
                  args.prompt_postfix, args.visual_width, args.visual_layers,
                  args.visual_head, args.attn_window, device).to(device)

    checkpoint = torch.load(args.checkpoint, map_location=device)

    model.load_state_dict(checkpoint)

    roc, ap = 0, 0
    if args.dataset == 'ucf':
        gt = np.load("./data/gt_ucf.npy")
        roc, ap = inference('ucf', model, test_loader, gt, device)
    elif args.dataset == 'me':
        gt = np.load("./data/gt_me.npy")
        roc, ap = inference('me', model, test_loader, gt, device)
    elif args.dataset == 'xd':
        gt = np.load("./data/gt_xd.npy")
        roc, ap = inference('xd', model, test_loader, gt, device)

    print(f'roc: {roc}, ap: {ap}')
