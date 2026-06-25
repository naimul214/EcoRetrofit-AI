"""
Domain randomization dataset generator for commercial building energy simulation.
Runs multiple annual episodes with varied sensor degradation and RBC threshold logic.
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


def get_action(indoor_temp: float, base_heat: float, base_cool: float) -> np.ndarray:
    """
    RBC controller utilizing domain-randomized setpoints.
    Sinergym 5-zone box limits generally: Heating [12.0, 23.25], Cooling [23.25, 30.0].
    """
    if indoor_temp < base_heat:
        # Full randomized heating strategy
        return np.array([base_heat, 30.0], dtype=np.float32)
    elif indoor_temp > base_cool:
        # Full randomized cooling strategy
        return np.array([12.0, base_cool], dtype=np.float32)
    else:
        # Do nothing - widen deadband
        return np.array([12.0, 30.0], dtype=np.float32)


def run_episode(env_id: str, episode: int, noise_scale: float, base_heat: float, base_cool: float) -> list[dict]:
    """
    Run a single full-year episode rollout with the given noise scale and setpoint parameters.
    """
    print(f"============================================================")
    print(f"--- Episode {episode}/10 ---")
    print(f"Sensor Noise Scale : {noise_scale}")
    print(f"RBC Base Heating   : {base_heat} C")
    print(f"RBC Base Cooling   : {base_cool} C")
    print(f"============================================================\n")
    
    # Setup environment specifically tailored to this episode parameters
    base_env: gym.Env = gym.make(env_id)
    env: gym.Env = SensorNoiseWrapper(base_env, noise_loc=0.0, noise_scale=noise_scale, target_index=11)
    
    try:
        obs, info = env.reset(seed=42 + episode)
        terminated: bool = False
        truncated: bool = False
        step_count: int = 0
        ep_reward: float = 0.0
        episode_data: list[dict] = []
        
        while not (terminated or truncated):
            action: np.ndarray = get_action(obs[11], base_heat, base_cool)
            next_obs, reward, terminated, truncated, info = env.step(action)
            
            row_data = {
                'episode': episode,
                'step': step_count,
                'noise_scale': noise_scale,
                'base_heat': base_heat,
                'base_cool': base_cool,
                'heating_setpoint': float(action[0]),
                'cooling_setpoint': float(action[1]),
                'reward': float(reward),
                'energy_penalty': info.get('reward_energy', 0.0),
                'comfort_penalty': info.get('reward_comfort', 0.0)
            }
            for i in range(17):
                row_data[f'obs_{i}'] = float(obs[i])
                row_data[f'next_obs_{i}'] = float(next_obs[i])
            episode_data.append(row_data)
            
            obs = next_obs
            ep_reward += reward
            step_count += 1
            
            if step_count % 10000 == 0:
                print(f"  -> Simulated Step: {step_count}/35040 | Episode Reward: {ep_reward:.2f}")
                
        print(f"Episode {episode} Finished! Yielded Steps: {step_count} | Ep Reward: {ep_reward:.2f}\n")
        return episode_data
    finally:
        env.close()


def save_dataset(data: list[dict], output_dir: Path) -> Path:
    """
    Save the combined episode datasets to a CSV file in the processed directory.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    df: pd.DataFrame = pd.DataFrame(data)
    print(f"Total Rows collected into DataFrame memory: {len(df)}")
    output_file: Path = output_dir / 'rbc_massive_baseline.csv'
    df.to_csv(output_file, index=False)
    print(f"Saved massive Domain Randomization Dataset precisely to: {output_file}")
    return output_file


def main() -> None:
    env_id: str = 'Eplus-5zone-cool-continuous-v1'
    print(f"Initializing Domain Randomization Generator on: {env_id}\n")
    
    all_data: list[dict] = []
    
    # 10 full-year episodes
    for episode in range(1, 11):
        # 1. Randomize Noise scale to simulate varying sensor degradation
        noise_scale: float = round(float(np.random.uniform(0.1, 1.0)), 3)
        
        # 2. Randomize RBC setpoints (ensuring Heating < Cooling & strict box capacity)
        base_heat: float = round(float(np.random.uniform(18.0, 21.0)), 3)
        base_cool: float = round(float(np.random.uniform(23.5, 25.0)), 3)
        
        episode_data: list[dict] = run_episode(env_id, episode, noise_scale, base_heat, base_cool)
        all_data.extend(episode_data)
        
    print("All 10 Episodes completed successfully!")
    
    default_dir: Path = PROJECT_ROOT / 'data' / 'processed'
    output_dir_str: str = os.environ.get('SIM_OUTPUT_DIR', str(default_dir))
    output_dir: Path = Path(output_dir_str)
    
    save_dataset(all_data, output_dir)


if __name__ == "__main__":
    main()
