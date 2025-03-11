import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.distributions import Normal
import gymnasium as gym
from gymnasium import spaces

class WasteCollectionEnv(gym.Env):
    """해양 쓰레기 수거 환경"""
    
    def __init__(self, lon_mesh, lat_mesh, initial_waste, U_interp, V_interp, ocean_mask):
        super().__init__()
        
        self.lon_mesh = lon_mesh
        self.lat_mesh = lat_mesh
        self.initial_waste = initial_waste
        self.U_interp = U_interp
        self.V_interp = V_interp
        self.ocean_mask = ocean_mask
        
        # 상태 공간: [현재위치_x, 현재위치_y, 주변_쓰레기_분포(8방향), 해류_U, 해류_V]
        self.observation_space = spaces.Box(
            low=np.array([lon_mesh.min(), lat_mesh.min()] + [0]*8 + [-1, -1]),
            high=np.array([lon_mesh.max(), lat_mesh.max()] + [1]*8 + [1, 1]),
            dtype=np.float32
        )
        
        # 행동 공간: [이동방향(각도), 이동속도]
        self.action_space = spaces.Box(
            low=np.array([-np.pi, 0]),
            high=np.array([np.pi, 1]),
            dtype=np.float32
        )
        
        # 환경 파라미터
        self.max_steps = 100
        self.dt = 1  # 시간 간격 (시간)
        self.collection_radius = 0.1  # 수거 반경 (도)
        self.fuel_consumption_rate = 0.01  # 연료 소비율
        
        self.reset()
    
    def get_state(self):
        """현재 상태 관측"""
        # 현재 위치 인덱스
        x_idx = np.argmin(np.abs(self.lon_mesh[0,:] - self.current_pos[0]))
        y_idx = np.argmin(np.abs(self.lat_mesh[:,0] - self.current_pos[1]))
        
        # 주변 8방향 쓰레기 분포
        surroundings = []
        for dy in [-1, 0, 1]:
            for dx in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                try:
                    surroundings.append(
                        self.waste[
                            max(0, min(y_idx + dy, self.waste.shape[0]-1)),
                            max(0, min(x_idx + dx, self.waste.shape[1]-1))
                        ]
                    )
                except IndexError:
                    surroundings.append(0)
        
        # 현재 위치의 해류
        current_u = self.U_interp[y_idx, x_idx]
        current_v = self.V_interp[y_idx, x_idx]
        
        return np.array([
            self.current_pos[0],
            self.current_pos[1]
        ] + surroundings + [
            current_u,
            current_v
        ], dtype=np.float32)
    
    def step(self, action):
        """환경 진행"""
        self.steps += 1
        
        # 행동 적용 (이동)
        angle, speed = action
        dx = speed * np.cos(angle) * self.dt
        dy = speed * np.sin(angle) * self.dt
        
        new_pos = [
            self.current_pos[0] + dx,
            self.current_pos[1] + dy
        ]
        
        # 경계 확인
        new_pos[0] = np.clip(new_pos[0], self.lon_mesh.min(), self.lon_mesh.max())
        new_pos[1] = np.clip(new_pos[1], self.lat_mesh.min(), self.lat_mesh.max())
        
        # 육지 충돌 확인
        x_idx = np.argmin(np.abs(self.lon_mesh[0,:] - new_pos[0]))
        y_idx = np.argmin(np.abs(self.lat_mesh[:,0] - new_pos[1]))
        
        if np.isnan(self.ocean_mask[y_idx, x_idx]):
            # 육지 충돌 시 이동 취소
            new_pos = self.current_pos
        
        self.current_pos = new_pos
        
        # 쓰레기 수거
        collected_waste = self._collect_waste()
        
        # 쓰레기 이동 시뮬레이션
        self._update_waste_distribution()
        
        # 보상 계산
        reward = (
            collected_waste * 100  # 수거한 쓰레기
            - speed * self.fuel_consumption_rate  # 연료 소비
            - 0.1  # 시간 페널티
        )
        
        # 종료 조건
        done = (self.steps >= self.max_steps)
        
        return self.get_state(), reward, done, False, {}
    
    def reset(self, seed=None):
        """환경 초기화"""
        super().reset(seed=seed)
        
        # 초기 위치 (랜덤)
        valid_positions = np.where(~np.isnan(self.ocean_mask))
        random_idx = np.random.randint(len(valid_positions[0]))
        self.current_pos = [
            self.lon_mesh[valid_positions[0][random_idx], valid_positions[1][random_idx]],
            self.lat_mesh[valid_positions[0][random_idx], valid_positions[1][random_idx]]
        ]
        
        # 쓰레기 분포 초기화
        self.waste = self.initial_waste.copy()
        self.steps = 0
        
        return self.get_state(), {}
    
    def _collect_waste(self):
        """현재 위치에서 쓰레기 수거"""
        x_idx = np.argmin(np.abs(self.lon_mesh[0,:] - self.current_pos[0]))
        y_idx = np.argmin(np.abs(self.lat_mesh[:,0] - self.current_pos[1]))
        
        # 수거 반경 내의 쓰레기 수거
        collection_mask = np.zeros_like(self.waste)
        for i in range(max(0, y_idx-1), min(self.waste.shape[0], y_idx+2)):
            for j in range(max(0, x_idx-1), min(self.waste.shape[1], x_idx+2)):
                if np.sqrt(
                    (self.lon_mesh[i,j] - self.current_pos[0])**2 +
                    (self.lat_mesh[i,j] - self.current_pos[1])**2
                ) <= self.collection_radius:
                    collection_mask[i,j] = 1
        
        collected = np.sum(self.waste * collection_mask)
        self.waste *= (1 - collection_mask)
        
        return collected
    
    def _update_waste_distribution(self):
        """쓰레기 이동 시뮬레이션"""
        waste_new = self.waste.copy()
        
        # 이류 항 계산
        dx = 0.01
        dy = 0.01
        
        waste_new[1:-1, 1:-1] -= (
            (self.U_interp[1:-1, 1:-1] * 
             (self.waste[1:-1, 2:] - self.waste[1:-1, :-2]) / (2 * dx)) * self.dt
        )
        
        waste_new[1:-1, 1:-1] -= (
            (self.V_interp[1:-1, 1:-1] * 
             (self.waste[2:, 1:-1] - self.waste[:-2, 1:-1]) / (2 * dy)) * self.dt
        )
        
        # 확산 항 계산
        diffusion_coef = 0.01
        waste_new[1:-1, 1:-1] += diffusion_coef * (
            (self.waste[2:, 1:-1] + self.waste[:-2, 1:-1] + 
             self.waste[1:-1, 2:] + self.waste[1:-1, :-2] - 
             4 * self.waste[1:-1, 1:-1]) / (dx * dy)
        ) * self.dt
        
        waste_new = waste_new * self.ocean_mask
        waste_new[waste_new < 0] = 0
        
        self.waste = waste_new

class Actor(nn.Module):
    """PPO Actor 네트워크"""
    
    def __init__(self, state_dim, action_dim):
        super().__init__()
        
        self.network = nn.Sequential(
            nn.Linear(state_dim, 64),
            nn.Tanh(),
            nn.Linear(64, 64),
            nn.Tanh(),
            nn.Linear(64, action_dim * 2)  # 평균과 표준편차
        )
        
    def forward(self, state):
        output = self.network(state)
        mean, log_std = output.chunk(2, dim=-1)
        
        # 각도는 -π ~ π로 제한
        mean[:,0] = torch.tanh(mean[:,0]) * np.pi
        # 속도는 0 ~ 1로 제한
        mean[:,1] = torch.sigmoid(mean[:,1])
        
        # 표준편차는 양수
        log_std = torch.clamp(log_std, -20, 2)
        std = log_std.exp()
        
        return mean, std

class Critic(nn.Module):
    """PPO Critic 네트워크"""
    
    def __init__(self, state_dim):
        super().__init__()
        
        self.network = nn.Sequential(
            nn.Linear(state_dim, 64),
            nn.Tanh(),
            nn.Linear(64, 64),
            nn.Tanh(),
            nn.Linear(64, 1)
        )
        
    def forward(self, state):
        return self.network(state)

class PPO:
    """PPO 알고리즘"""
    
    def __init__(self, env):
        self.env = env
        
        state_dim = env.observation_space.shape[0]
        action_dim = env.action_space.shape[0]
        
        self.actor = Actor(state_dim, action_dim)
        self.critic = Critic(state_dim)
        
        self.actor_optimizer = optim.Adam(self.actor.parameters(), lr=3e-4)
        self.critic_optimizer = optim.Adam(self.critic.parameters(), lr=1e-3)
        
        self.clip_param = 0.2
        self.max_grad_norm = 0.5
        self.ppo_epochs = 10
        self.batch_size = 64
        self.gamma = 0.99
        self.gae_lambda = 0.95
        
    def select_action(self, state):
        """행동 선택"""
        with torch.no_grad():
            state = torch.FloatTensor(state).unsqueeze(0)
            mean, std = self.actor(state)
            dist = Normal(mean, std)
            action = dist.sample()
            log_prob = dist.log_prob(action).sum(dim=-1)
            
        return action.numpy()[0], log_prob.numpy()[0]
    
    def update(self, trajectories):
        """정책 업데이트"""
        # 데이터 준비
        states = torch.FloatTensor(np.array([t[0] for t in trajectories]))
        actions = torch.FloatTensor(np.array([t[1] for t in trajectories]))
        old_log_probs = torch.FloatTensor(np.array([t[2] for t in trajectories]))
        rewards = torch.FloatTensor(np.array([t[3] for t in trajectories]))
        next_states = torch.FloatTensor(np.array([t[4] for t in trajectories]))
        dones = torch.FloatTensor(np.array([t[5] for t in trajectories]))
        
        # GAE 계산
        with torch.no_grad():
            values = self.critic(states)
            next_values = self.critic(next_states)
            
            advantages = torch.zeros_like(rewards)
            returns = torch.zeros_like(rewards)
            advantage = 0
            next_value = next_values[-1]
            
            for t in reversed(range(len(rewards))):
                td_error = (
                    rewards[t] +
                    self.gamma * next_values[t] * (1 - dones[t]) -
                    values[t]
                )
                advantage = (
                    td_error +
                    self.gamma * self.gae_lambda * (1 - dones[t]) * advantage
                )
                advantages[t] = advantage
                returns[t] = advantage + values[t]
        
        # PPO 업데이트
        for _ in range(self.ppo_epochs):
            # 미니배치 샘플링
            indices = np.random.permutation(len(trajectories))
            
            for start in range(0, len(trajectories), self.batch_size):
                end = start + self.batch_size
                batch_indices = indices[start:end]
                
                batch_states = states[batch_indices]
                batch_actions = actions[batch_indices]
                batch_old_log_probs = old_log_probs[batch_indices]
                batch_advantages = advantages[batch_indices]
                batch_returns = returns[batch_indices]
                
                # Actor 업데이트
                mean, std = self.actor(batch_states)
                dist = Normal(mean, std)
                log_probs = dist.log_prob(batch_actions).sum(dim=-1)
                
                ratio = torch.exp(log_probs - batch_old_log_probs)
                surr1 = ratio * batch_advantages
                surr2 = torch.clamp(
                    