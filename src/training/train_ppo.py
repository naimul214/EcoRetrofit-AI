"""
PPO model training pipeline for commercial building climate setpoint optimization.
Saves model checkpoints and normalization statistics using pathlib and configurable paths.
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
from stable_baselines3.common.callbacks import CheckpointCallback


def make_env() -> gym.Env:
    """
    Instantiate and return the basic Sinergym environment wrapped with SensorNoiseWrapper.
    """
    env: gym.Env = gym.make('Eplus-5zone-cool-discrete-v1')
    env = SensorNoiseWrapper(env)
    return env


def train_model(env: VecNormalize, total_timesteps: int, weights_dir: Path, checkpoints_dir: Path) -> None:
    """
    Configure stable-baselines3 PPO model and run the learning loop.
    """
    weights_dir.mkdir(parents=True, exist_ok=True)
    checkpoints_dir.mkdir(parents=True, exist_ok=True)

    # Instantiate the PPO model
    model: PPO = PPO('MlpPolicy', env, verbose=1, learning_rate=3e-4, clip_range=0.2)
    
    # Checkpoint callback writes directly to the repository weights folder.
    checkpoint_callback: CheckpointCallback = CheckpointCallback(
        save_freq=1000000,
        save_path=str(checkpoints_dir),
        name_prefix='ppo_discrete'
    )
    
    print(f"\n[*] Commencing {total_timesteps} Step PPO Learn Epochs...")
    model.learn(total_timesteps=total_timesteps, callback=checkpoint_callback, progress_bar=True)
    
    # Save final model and VecNormalize statistics.
    model_path: Path = weights_dir / 'ppo_discrete_ecoretrofit_5M'
    model.save(str(model_path))

    vec_norm_path: Path = weights_dir / 'vec_normalize_discrete.pkl'
    env.save(str(vec_norm_path))
    
    print(f"\n[*] PPO Model securely saved internally to {model_path}.zip")
    print(f"[*] VecNormalize statistics securely saved internally to {vec_norm_path}")


def main() -> None:
    print("==================================================")
    print("Initializing Stable Baselines 3 PPO Training Pipeline")
    print("==================================================")
    
    # Wrap that environment in DummyVecEnv
    venv: DummyVecEnv = DummyVecEnv([make_env])
    
    # Finally, wrap it in VecNormalize
    env: VecNormalize = VecNormalize(venv, norm_obs=True, norm_reward=True, clip_obs=10.)
    
    # Resolve paths from environment variables with path lib defaults
    default_weights_dir: Path = PROJECT_ROOT / 'models' / 'weights'
    weights_dir_str: str = os.environ.get('WEIGHTS_DIR', str(default_weights_dir))
    weights_dir: Path = Path(weights_dir_str)
    
    default_checkpoints_dir: Path = weights_dir / 'checkpoints'
    checkpoints_dir_str: str = os.environ.get('CHECKPOINTS_DIR', str(default_checkpoints_dir))
    checkpoints_dir: Path = Path(checkpoints_dir_str)
    
    train_model(
        env=env,
        total_timesteps=5000000,
        weights_dir=weights_dir,
        checkpoints_dir=checkpoints_dir
    )


if __name__ == '__main__':
    main()
