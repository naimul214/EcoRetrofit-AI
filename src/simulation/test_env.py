import gymnasium as gym
import sinergym
from typing import Any, Tuple, Dict

def main() -> None:
    # Initialize the basic Sinergym environment
    env_id: str = 'Eplus-5zone-hot-continuous-v1'
    print(f"Initializing Sinergym environment: {env_id}")
    env: gym.Env = gym.make(env_id)
    
    try:
        # Reset the environment
        obs: Any
        info: Dict[str, Any]
        obs, info = env.reset()
        print(f"Environment reset. Initial observation: {obs}")
        
        # Run a standard env.step() loop for 10 iterations
        iterations: int = 10
        print(f"Running simulation for {iterations} steps...")
        
        for step in range(iterations):
            # Sample a random action
            action: Any = env.action_space.sample()
            
            # Step the environment
            obs, reward, terminated, truncated, info = env.step(action)
            
            # Print the current step, the reward, and the observation array
            print(f"Step {step + 1}:")
            print(f"  Reward     : {reward}")
            print(f"  Observation: {obs}")
            print("-" * 40)
            
            if terminated or truncated:
                print("Episode finished early.")
                break
                
    finally:
        # Cleanly close the environment
        print("Closing the environment.")
        env.close()

if __name__ == "__main__":
    main()
