"""
Rule-Based Controller (RBC) for commercial building heating and cooling setpoint control.
Simulates a full 1-year episode in the Sinergym environment with sensor noise.
"""

import os
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import gymnasium as gym
import sinergym

# Resolve project root and ensure it is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.simulation.noise_wrapper import SensorNoiseWrapper


def rbc_action(obs: np.ndarray) -> np.ndarray:
    """
    Rule-Based Controller mapping the indoor temperature (index 11) to continuous HVAC setpoints.
    Sinergym action space for 5zone-hot-continuous: [heating_setpoint, cooling_setpoint]
    Default absolute limits are:
    Heating: [15.0, 22.5]
    Cooling: [22.5, 30.0]
    """
    indoor_temp: float = obs[11]
    
    if indoor_temp < 20.0:
        # Full heating (Max heat: 23.25, Max cool setpoint: 30.0 so cooling is off)
        return np.array([23.25, 30.0], dtype=np.float32)
    elif indoor_temp > 24.0:
        # Full cooling (Min heat setpoint: 12.0 so heating is off, Min cool: 23.25)
        return np.array([12.0, 23.25], dtype=np.float32)
    else:
        # Do nothing - wide deadband to save energy
        return np.array([12.0, 30.0], dtype=np.float32)


def setup_environment(env_id: str, noise_scale: float) -> gym.Env:
    """
    Initialize and wrap the Sinergym environment with SensorNoiseWrapper.
    """
    print(f"Initializing base Sinergym environment: {env_id}")
    base_env: gym.Env = gym.make(env_id)
    # Wrap it with our Sim-to-Real SensorNoiseWrapper
    env: gym.Env = SensorNoiseWrapper(base_env, noise_loc=0.0, noise_scale=noise_scale, target_index=11)
    return env


def run_rollout(env: gym.Env, steps: int = 35040) -> list[dict]:
    """
    Run a full episode rollout of the RBC controller on the wrapped environment.
    """
    print("Resetting environment for a full 1-year episode...")
    obs, info = env.reset(seed=42)
    
    terminated: bool = False
    truncated: bool = False
    data: list[dict] = []
    total_reward: float = 0.0
    step_count: int = 0
    
    print(f"Starting RBC Simulation loop (Max Steps: {steps})...")
    
    while not (terminated or truncated) and step_count < steps:
        action: np.ndarray = rbc_action(obs)
        next_obs, reward, terminated, truncated, info = env.step(action)
        
        data.append({
            'step': step_count,
            'indoor_temp': obs[11],
            'heating_setpoint': float(action[0]),
            'cooling_setpoint': float(action[1]),
            'reward': float(reward),
            'next_indoor_temp': float(next_obs[11]),
            'energy_penalty': info.get('reward_energy', 0.0),
            'comfort_penalty': info.get('reward_comfort', 0.0)
        })
        
        total_reward += reward
        obs = next_obs
        step_count += 1
        
        if step_count % 5000 == 0:
            print(f"  -> Simulated Step: {step_count} / {steps} | Cumulative Reward: {total_reward:.2f}")
            
    print(f"\nEpisode finished successfully!")
    print(f"Total Steps: {step_count}")
    print(f"Sum of Total Reward: {total_reward:.2f}")
    return data


def save_results(data: list[dict], output_dir: Path) -> Path:
    """
    Save simulation data to a CSV file in the specified output directory.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    df: pd.DataFrame = pd.DataFrame(data)
    output_file: Path = output_dir / 'rbc_baseline.csv'
    df.to_csv(output_file, index=False)
    print(f"Saved RBC Baseline results securely to: {output_file}")
    return output_file


def main() -> None:
    env_id: str = 'Eplus-5zone-hot-continuous-v1'
    env: gym.Env = setup_environment(env_id, noise_scale=0.5)
    
    try:
        data: list[dict] = run_rollout(env, steps=35040)
        
        # Read output directory from environment variable with fallback
        default_dir: Path = PROJECT_ROOT / 'data' / 'processed'
        output_dir_str: str = os.environ.get('SIM_OUTPUT_DIR', str(default_dir))
        output_dir: Path = Path(output_dir_str)
        
        save_results(data, output_dir)
    finally:
        env.close()


if __name__ == "__main__":
    main()
