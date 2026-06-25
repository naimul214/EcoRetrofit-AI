"""
PPO model evaluation pipeline for commercial building climate setpoint optimization.
Loads normalization statistics and policy constraints using pathlib-based path resolution.
"""

import os
import sys
from pathlib import Path
import gymnasium as gym
import sinergym

# Resolve project root and ensure it is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.simulation.noise_wrapper import SensorNoiseWrapper
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize


def make_env() -> gym.Env:
    """
    Instantiate and return the basic Sinergym environment wrapped with SensorNoiseWrapper.
    """
    env: gym.Env = gym.make('Eplus-5zone-cool-discrete-v1')
    env = SensorNoiseWrapper(env)
    return env


def evaluate_model(env: VecNormalize, model_path: Path, max_steps: int = 35040) -> float:
    """
    Load pre-trained model constraints and execute the evaluation loop.
    """
    # 2. Load model linking securely
    model: PPO = PPO.load(str(model_path), env=env)
    print("[*] Successfully mapped Pre-Trained constraints directly!")
    
    # 3. Simulate Sinergym Native Iterations
    obs = env.reset()
    
    total_reward: float = 0.0
    steps: int = 0
    
    print(f"\n[*] Starting {max_steps}-step Simulation Process...")
    
    while steps < max_steps:
        # Deterministically extract explicit Setpoints
        action, _states = model.predict(obs, deterministic=True)
        
        # Step vector-array map
        obs, reward, done, info = env.step(action)
        
        total_reward += float(reward[0])
        steps += 1
        
        if done[0]:
            print(f"[*] Environment sequence dynamically concluded natively at Step {steps}")
            break
            
    return total_reward


def main() -> None:
    print("==================================================")
    print("Initializing Stable Baselines 3 PPO Evaluation Pipeline")
    print("==================================================")

    # Resolve paths from environment variables or use pathlib defaults
    default_vec_norm_path: Path = PROJECT_ROOT / 'models' / 'weights' / 'vec_normalize_discrete.pkl'
    vec_norm_path_str: str = os.environ.get('VEC_NORM_PATH', str(default_vec_norm_path))
    vec_norm_path: Path = Path(vec_norm_path_str)

    default_model_path: Path = PROJECT_ROOT / 'models' / 'weights' / 'ppo_discrete_ecoretrofit_5M.zip'
    model_path_str: str = os.environ.get('EVAL_MODEL_PATH', str(default_model_path))
    model_path: Path = Path(model_path_str)

    if not vec_norm_path.exists():
        raise FileNotFoundError(f"VecNormalize statistics not found at: {vec_norm_path}")
    if not model_path.exists():
        raise FileNotFoundError(f"Evaluation model not found at: {model_path}")
    
    # 1. Environment Instantiation
    print("[*] Booting Sinergym Subprocess via Eplus-5zone-cool-discrete-v1...")
    venv: DummyVecEnv = DummyVecEnv([make_env])
    
    # CRITICAL: Load the normalization statistics smoothly
    env: VecNormalize = VecNormalize.load(str(vec_norm_path), venv)
    
    # CRITICAL: Disable training and reward normalization cleanly 
    env.training = False
    env.norm_reward = False
    
    try:
        total_reward: float = evaluate_model(env=env, model_path=model_path, max_steps=35040)
        
        print("\n==================================================")
        print(f"Simulation Finished. Total AI Reward: {total_reward:.2f}")
        print("==================================================")
    finally:
        env.close()


if __name__ == '__main__':
    main()
