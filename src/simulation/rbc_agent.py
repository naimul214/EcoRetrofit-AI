import os
import sys
import pandas as pd
import numpy as np
import gymnasium as gym
import sinergym

# Ensure local imports from src work perfectly regardless of execution path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from src.simulation.noise_wrapper import SensorNoiseWrapper

def rbc_action(obs: np.ndarray) -> np.ndarray:
    """
    Rule-Based Controller mapping the indoor temperature (index 11) to continuous HVAC setpoints.
    Sinergym action space for 5zone-hot-continuous: [heating_setpoint, cooling_setpoint]
    Default absolute limits are:
    Heating: [15.0, 22.5]
    Cooling: [22.5, 30.0]
    """
    indoor_temp = obs[11]
    
    if indoor_temp < 20.0:
        # Full heating (Max heat: 23.25, Max cool setpoint: 30.0 so cooling is off)
        return np.array([23.25, 30.0], dtype=np.float32)
    elif indoor_temp > 24.0:
        # Full cooling (Min heat setpoint: 12.0 so heating is off, Min cool: 23.25)
        return np.array([12.0, 23.25], dtype=np.float32)
    else:
        # Do nothing - wide deadband to save energy
        return np.array([12.0, 30.0], dtype=np.float32)

def main() -> None:
    env_id = 'Eplus-5zone-hot-continuous-v1'
    print(f"Initializing base Sinergym environment: {env_id}")
    base_env = gym.make(env_id)
    
    # Wrap it with our newly created Sim-to-Real SensorNoiseWrapper
    env = SensorNoiseWrapper(base_env, noise_loc=0.0, noise_scale=0.5, target_index=11)
    
    # Reset Environment for new episode
    print("Resetting environment for a full 1-year episode...")
    obs, info = env.reset(seed=42)
    
    terminated = False
    truncated = False
    data = []
    total_reward = 0.0
    step_count = 0
    
    print("Starting RBC Simulation loop (Expected: 35040 steps)...")
    
    # Run the continuous environment loop
    while not (terminated or truncated):
        # 1. Ask agent for action
        action = rbc_action(obs)
        
        # 2. Step environment
        next_obs, reward, terminated, truncated, info = env.step(action)
        
        # 3. Collect Data
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
        
        # Provide visual heartbeat to ensure it is running in Docker smoothly
        if step_count % 5000 == 0:
            print(f"  -> Simulated Step: {step_count} / 35040 | Cumulative Reward: {total_reward:.2f}")

    print(f"\nEpisode finished successfully!")
    print(f"Total Steps: {step_count}")
    print(f"Sum of Total Reward: {total_reward:.2f}")
    
    # 4. Save gathered Data to a Pandas DataFrame & CSV
    df = pd.DataFrame(data)
    
    output_dir = '/app/data/processed'
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = os.path.join(output_dir, 'rbc_baseline.csv')
    df.to_csv(output_file, index=False)
    print(f"Saved RBC Baseline results securely to: {output_file}")
    
    env.close()

if __name__ == "__main__":
    main()
