import os
import sys
import gymnasium as gym

# Add src to python path to import simulation modules dynamically
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import sinergym
from simulation.noise_wrapper import SensorNoiseWrapper
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
DEFAULT_MODEL_RELATIVE = os.path.join('models', 'weights', 'ppo_discrete_ecoretrofit_5M.zip')
VEC_NORM_RELATIVE = os.path.join('models', 'weights', 'vec_normalize_discrete.pkl')


def make_env() -> gym.Env:
    env = gym.make('Eplus-5zone-cool-discrete-v1')
    env = SensorNoiseWrapper(env)
    return env


def resolve_model_path(base_dir: str) -> str:
    model_override = os.environ.get('EVAL_MODEL_PATH', '').strip()
    if model_override:
        if os.path.isabs(model_override):
            return model_override
        return os.path.join(base_dir, model_override)
    return os.path.join(base_dir, DEFAULT_MODEL_RELATIVE)


def main() -> None:
    print("==================================================")
    print("Initializing Stable Baselines 3 PPO Evaluation Pipeline")
    print("==================================================")

    vec_norm_path = os.path.join(PROJECT_ROOT, VEC_NORM_RELATIVE)
    model_path = resolve_model_path(PROJECT_ROOT)

    if not os.path.exists(vec_norm_path):
        raise FileNotFoundError(f"VecNormalize statistics not found at: {vec_norm_path}")
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Evaluation model not found at: {model_path}")
    
    # 1. Environment Instantiation Native Sequence
    print("[*] Booting Sinergym Subprocess via Eplus-5zone-cool-discrete-v1...")
    env = DummyVecEnv([make_env])
    
    # CRITICAL: Load the normalization statistics smoothly
    env = VecNormalize.load(vec_norm_path, env)
    
    # CRITICAL: Disable training and reward normalization cleanly 
    # Mapped environments will explicitly compute the raw Sinergym environmental total dynamically
    env.training = False
    env.norm_reward = False
    
    # 2. Load model linking securely
    model = PPO.load(model_path, env=env)
    print("[*] Successfully mapped Pre-Trained constraints directly!")
    
    # 3. Simulate Sinergym Native Iterations explicitly mapped
    obs = env.reset()
    
    total_reward = 0.0
    steps = 0
    max_steps = 35040 # Full year precisely mapped dynamically across iteration lengths sequentially (15-min intervals)
    
    print(f"\n[*] Starting {max_steps}-step Simulation Process Native Bounds...")
    
    while steps < max_steps:
        # Deterministically extract explicit Setpoints seamlessly bounds targeting unweighted outputs seamlessly
        action, _states = model.predict(obs, deterministic=True)
        
        # Step vector-array map bounds
        obs, reward, done, info = env.step(action)
        
        # Supervised output scalar mapping sequences tracked internally 
        total_reward += reward[0] # Base Array index securely mapped internally gracefully
        steps += 1
        
        if done[0]:
            print(f"[*] Environment sequence dynamically concluded natively at Step {steps}")
            break
            
    # Sinergym Cleanup logic mapping
    env.close()
    
    print("\n==================================================")
    print(f"Simulation Finished. Total AI Reward: {total_reward:.2f}")
    print("==================================================")

if __name__ == '__main__':
    main()
