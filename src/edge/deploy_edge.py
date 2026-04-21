import time
import requests
import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
import gymnasium as gym
from gymnasium import spaces

class DummyHVACEnv(gym.Env):
    def __init__(self):
        super().__init__()
        self.observation_space = spaces.Box(low=-5e6, high=5e6, shape=(17,), dtype=np.float32)
        self.action_space = spaces.Discrete(10)

    def step(self, action):
        return np.zeros(17), 0, False, False, {}

    def reset(self, seed=None):
        return np.zeros(17), {}

BMS_API_URL = 'http://127.0.0.1:8000/api/v1/zones/1'

print('[SYSTEM] Booting Edge Inference Engine...')

dummy_env = DummyVecEnv([lambda: DummyHVACEnv()])
env = VecNormalize.load('EcoRetrofit-Edge/vec_normalize_discrete.pkl', dummy_env)
env.training = False
env.norm_reward = False

print('[SYSTEM] Loading 3M-Step Golden Model...')
model = PPO.load('EcoRetrofit-Edge/golden_model.zip')

print(f'[SYSTEM] Connecting to Mock BMS Network at {BMS_API_URL}...')
print('='*60)

while True:
    try:
        response = requests.get(BMS_API_URL, timeout=2)
        zone_data = response.json()
        current_temp = zone_data['indoor_temp']
        
        raw_sensor_data = np.zeros(17, dtype=np.float32)
        raw_sensor_data[11] = current_temp
        
        start_time = time.perf_counter()
        normalized_obs = env.normalize_obs(raw_sensor_data)
        action, _states = model.predict(normalized_obs, deterministic=True)
        latency_ms = (time.perf_counter() - start_time) * 1000
        
        print(f'[LIVE] BMS Temp: {current_temp}°C | AI Action: {action} | Latency: {latency_ms:.2f} ms')
        
    except requests.exceptions.ConnectionError:
        print('[ERROR] Connection refused. Is the mock_api.py server running on port 8000?')
        break
        
    time.sleep(1.5)

print('='*60)
print('[SYSTEM] 5-Cycle Test Complete.')
