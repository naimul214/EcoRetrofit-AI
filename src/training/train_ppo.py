import os
import sys
import gymnasium as gym
import sinergym

# Add src to python path to import simulation modules dynamically
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from simulation.noise_wrapper import SensorNoiseWrapper
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
from stable_baselines3.common.callbacks import CheckpointCallback

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
WEIGHTS_DIR = os.path.join(PROJECT_ROOT, 'models', 'weights')
CHECKPOINTS_DIR = os.path.join(WEIGHTS_DIR, 'checkpoints')


def make_env() -> gym.Env:
    env = gym.make('Eplus-5zone-cool-discrete-v1')
    env = SensorNoiseWrapper(env)
    return env


def main() -> None:
    print("==================================================")
    print("Initializing Stable Baselines 3 PPO Training Pipeline")
    print("==================================================")
    
    # Wrap that environment in DummyVecEnv
    env = DummyVecEnv([make_env])
    
    # Finally, wrap it in VecNormalize
    env = VecNormalize(env, norm_obs=True, norm_reward=True, clip_obs=10.)
    
    # Instantiate the PPO model
    model = PPO('MlpPolicy', env, verbose=1, learning_rate=3e-4, clip_range=0.2)
    
    os.makedirs(WEIGHTS_DIR, exist_ok=True)
    os.makedirs(CHECKPOINTS_DIR, exist_ok=True)

    # Checkpoint callback writes directly to the repository weights folder.
    checkpoint_callback = CheckpointCallback(
        save_freq=1000000,
        save_path=CHECKPOINTS_DIR,
        name_prefix='ppo_discrete'
    )
    
    # Train the model limits deep scaling inherently
    print("\n[*] Commencing 5,000,000 Step PPO Learn Epochs natively mapped...")
    model.learn(total_timesteps=5000000, callback=checkpoint_callback, progress_bar=True)
    
    # Save final model and VecNormalize statistics beside checkpoints.
    model_path = os.path.join(WEIGHTS_DIR, 'ppo_discrete_ecoretrofit_5M')
    model.save(model_path)

    vec_norm_path = os.path.join(WEIGHTS_DIR, 'vec_normalize_discrete.pkl')
    env.save(vec_norm_path)
    
    print(f"\n[*] PPO Model securely saved internally to {model_path}.zip")
    print(f"[*] VecNormalize statistics securely saved internally to {vec_norm_path}")

if __name__ == '__main__':
    main()
