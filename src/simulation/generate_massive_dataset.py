import os
import sys
import pandas as pd
import numpy as np
import gymnasium as gym
import sinergym

# Define correct path to include the noise wrapper
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
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

def main() -> None:
    env_id = 'Eplus-5zone-cool-continuous-v1'
    print(f"Initializing Domain Randomization Generator on: {env_id}\n")
    
    data = []
    
    # 10 full-year episodes
    for episode in range(1, 11):
        # 1. Randomize Noise scale to simulate varying sensor degradation
        noise_scale = round(np.random.uniform(0.1, 1.0), 3)
        
        # 2. Randomize RBC setpoints (ensuring Heating < Cooling & strict box capacity)
        # Heating randomly between 18.0 and 21.0
        base_heat = round(np.random.uniform(18.0, 21.0), 3)
        # Cooling randomly between 23.5 and 25.0
        base_cool = round(np.random.uniform(23.5, 25.0), 3)
        
        print(f"============================================================")
        print(f"--- Episode {episode}/10 ---")
        print(f"Sensor Noise Scale : {noise_scale}")
        print(f"RBC Base Heating   : {base_heat} C")
        print(f"RBC Base Cooling   : {base_cool} C")
        print(f"============================================================\n")
        
        # Setup environment specifically tailored to this episode parameters
        base_env = gym.make(env_id)
        env = SensorNoiseWrapper(base_env, noise_loc=0.0, noise_scale=noise_scale, target_index=11)
        
        # Reset natively mapping a new seed corresponding to the episode iter
        obs, info = env.reset(seed=42 + episode)
        terminated = False
        truncated = False
        step_count = 0
        ep_reward = 0.0
        
        # Continuous sequence execution logic
        while not (terminated or truncated):
            action = get_action(obs[11], base_heat, base_cool)
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
            data.append(row_data)
            
            obs = next_obs
            ep_reward += reward
            step_count += 1
            
            if step_count % 10000 == 0:
                print(f"  -> Simulated Step: {step_count}/35040 | Episode Reward: {ep_reward:.2f}")

        print(f"Episode {episode} Finished! Yielded Steps: {step_count} | Ep Reward: {ep_reward:.2f}\n")
        env.close()
        
    print("All 10 Episodes completed successfully!")
    df = pd.DataFrame(data)
    print(f"Total Rows collected into DataFrame memory: {len(df)}")
    
    # Save Massive payload aggregated data securely
    output_dir = '/app/data/processed'
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, 'rbc_massive_baseline.csv')
    df.to_csv(output_file, index=False)
    print(f"Saved massive Domain Randomization Dataset precisely to: {output_file}")

if __name__ == "__main__":
    main()
