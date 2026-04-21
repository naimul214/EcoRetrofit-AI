import sys
import torch
import torch.nn as nn
from pathlib import Path
from stable_baselines3 import PPO

# Project root is two levels above this file (src/training/export_onnx.py -> root)
PROJECT_ROOT: Path = Path(__file__).parents[2]

class OnnxablePolicy(nn.Module):
    def __init__(self, extractor, action_net):
        super().__init__()
        self.extractor = extractor
        self.action_net = action_net

    def forward(self, observation):
        action_hidden, _ = self.extractor(observation)
        logits = self.action_net(action_hidden)
        action = torch.argmax(logits, dim=1)
        return action

def export_model() -> None:
    model_path = PROJECT_ROOT / "EcoRetrofit-Edge" / "golden_model.zip"
    
    if not model_path.exists():
        print(f"Model zip file not found at: {model_path}")
        sys.exit(1)
        
    print(f"Loading model from: {model_path}")
    
    model: PPO = PPO.load(str(model_path), device="cpu")
    
    # Create the purely deterministic network wrapper
    onnxable_model = OnnxablePolicy(model.policy.mlp_extractor, model.policy.action_net)
    onnxable_model.eval()
    
    dummy_input: torch.Tensor = torch.randn(1, 17)
    
    export_path = PROJECT_ROOT / "src" / "edge" / "models" / "ecoretrofit_3M.onnx"
    export_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Export explicitly using JIT tracing fallback instead of dynamo if possible
    # We specify dynamo_export=False implicitly by providing opset_version.
    torch.onnx.export(
        onnxable_model,
        dummy_input,
        str(export_path),
        opset_version=11,
        input_names=["observation"],
        output_names=["action"]
    )
    
    print(f"Model successfully exported to: {export_path}")

if __name__ == "__main__":
    export_model()
