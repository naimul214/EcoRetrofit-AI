import gymnasium as gym
import sinergym
from typing import Any, Dict
from noise_wrapper import SensorNoiseWrapper
import numpy as np

def main() -> None:
    env_id: str = 'Eplus-5zone-hot-continuous-v1'
    print(f"Initializing base Sinergym environment: {env_id}")
    
    # Initialize the base environment
    base_env: gym.Env = gym.make(env_id)
    
    # Wrap it to simulate noise
    noisy_env: gym.Env = SensorNoiseWrapper(base_env, noise_loc=0.0, noise_scale=0.5, target_index=11)
    
    try:
        # Reset the environment (Using base environment for raw obs to compare)
        # We need to manually reset the base_env and format the noise to demonstrate the difference properly
        print("Resetting environment...")
        
        # In a real run we step the noisy env, but for testing exactly the same step we will fetch raw obs then wrap
        raw_obs, info = base_env.reset(seed=42)
        
        # Print the exact value before noise is added
        print(f"\n[Raw Observation] Size: {len(raw_obs)}")
        print(f"Target Index (11) - Indoor Temperature [Raw]: {raw_obs[11]}")
        
        # Now pass the raw obs manually through the wrapper's observation logic to see exact transformation
        wrapper_instance = noisy_env.unwrapped if hasattr(noisy_env, "unwrapped") else noisy_env
        noisy_obs = noisy_env.observation(raw_obs) # type: ignore
        
        print(f"\n[Noisy Observation] Size: {len(noisy_obs)}")
        print(f"Target Index (11) - Indoor Temperature [Noisy]: {noisy_obs[11]}")
        
        variance = abs(noisy_obs[11] - raw_obs[11])
        print(f"\nApplied Variance at Index 11: {variance:.4f}")

    finally:
        # Cleanly close the environment
        print("\nClosing the environment.")
        base_env.close()

if __name__ == "__main__":
    main()
