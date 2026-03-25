import numpy as np
import gymnasium as gym
from typing import Any

class SensorNoiseWrapper(gym.ObservationWrapper):
    """
    Simulates real-world sensor drift by injecting Gaussian noise
    into the observation array.
    """
    
    def __init__(self, env: gym.Env, noise_loc: float = 0.0, noise_scale: float = 0.5, target_index: int = 11):
        """
        Initializes the noise wrapper.

        Args:
            env (gym.Env): The Sinergym environment to wrap.
            noise_loc (float): Mean of the Gaussian noise (default: 0.0).
            noise_scale (float): Standard deviation of the Gaussian noise (default: 0.5).
            target_index (int): Index of the observation array to inject noise into (default: 11 for indoor temp).
        """
        super().__init__(env)
        self.noise_loc = noise_loc
        self.noise_scale = noise_scale
        self.target_index = target_index

    def observation(self, obs: Any) -> Any:
        """
        Overrides the observation to inject noise.

        Args:
            obs (Any): The original observation array from the environment.

        Returns:
            Any: The modified observation array with noise applied to the target index.
        """
        # Ensure obs is a numpy array and we don't modify the original reference memory in place
        obs_copy = np.array(obs, copy=True)
        
        # Inject Gaussian noise specifically into the defined target index
        if self.target_index < len(obs_copy):
            noise: float = np.random.normal(loc=self.noise_loc, scale=self.noise_scale)
            obs_copy[self.target_index] += noise
            
        return obs_copy
