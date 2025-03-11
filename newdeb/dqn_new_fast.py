import gymnasium as gym
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import random
import time
from collections import deque
from torch.utils.data import DataLoader, TensorDataset

# ✅ GPU 연산 최적화 적용
torch.backends.cudnn.benchmark = True
torch.backends.cudnn.enabled = True

# ✅ CUDA 설정 (GPU가 없으면 CPU 사용)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using device: {device}")

# ✅ 1️⃣ PER (Prioritized Experience Replay) 적용
class PrioritizedReplayBuffer:
    def __init__(self, capacity, alpha=0.6):
        self.capacity = capacity
        self.buffer = []
        self.priorities = np.zeros((capacity,), dtype=np.float32)
        self.alpha = alpha
        self.position = 0

    def add(self, experience, error):
        priority = (abs(error) + 1e-5) ** self.alpha
        if len(self.buffer) < self.capacity:
            self.buffer.append(experience)
        else:
            self.buffer[self.position] = experience

        self.priorities[self.position] = priority
        self.position = (self.position + 1) % self.capacity

    def sample(self, batch_size, beta=0.4):
        probs = self.priorities[: len(self.buffer)] ** self.alpha
        probs /= probs.sum()

        indices = np.random.choice(len(self.buffer), batch_size, p=probs)
        experiences = [self.buffer[idx] for idx in indices]

        return experiences, indices

    def update_priorities(self, indices, errors):
        for idx, error in zip(indices, errors):
            self.priorities[idx] = (abs(error) + 1e-5) ** self.alpha

# ✅ 2️⃣ Noisy Net 적용 (ε-greedy 탐색 최적화)
class NoisyLinear(nn.Module):
    def __init__(self, in_features, out_features):
        super(NoisyLinear, self).__init__()
        self.mu_weight = nn.Parameter(torch.FloatTensor(out_features, in_features))
        self.sigma_weight = nn.Parameter(torch.FloatTensor(out_features, in_features))
        self.register_buffer("epsilon_weight", torch.FloatTensor(out_features, in_features))
        self.reset_parameters()

    def reset_parameters(self):
        self.mu_weight.data.uniform_(-0.2, 0.2)
        self.sigma_weight.data.fill_(0.017)

    def forward(self, x):
        return torch.nn.functional.linear(x, self.mu_weight + self.sigma_weight * self.epsilon_weight)

# ✅ 3️⃣ Double DQN 적용 (Q-value 안정화)
class DoubleDQN(nn.Module):
    def __init__(self, input_dim, output_dim):
        super(DoubleDQN, self).__init__()
        self.fc1 = NoisyLinear(input_dim, 128)
        self.fc2 = NoisyLinear(128, 128)
        self.fc3 = NoisyLinear(128, output_dim)

    def forward(self, x):
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc2(x))
        return self.fc3(x)

# ✅ 4️⃣ Multi-Step Learning 적용 (n=3)
n_step = 3
gamma_n = 0.99 ** n_step

# ✅ 5️⃣ 학습 루프 (최적화 적용)
def train_dqn(env, episodes=500, batch_size=128, gamma=0.99, lr=0.001):
    model = torch.compile(DoubleDQN(input_dim=4, output_dim=4).to(device))  # ✅ torch.compile() 적용
    target_model = DoubleDQN(input_dim=4, output_dim=4).to(device)
    target_model.load_state_dict(model.state_dict())

    optimizer = optim.Adam(model.parameters(), lr=lr)
    loss_fn = nn.MSELoss()
    buffer = PrioritizedReplayBuffer(capacity=50000)

    start_time = time.time()

    for episode in range(episodes):
        episode_start = time.time()
        state = env.reset()
        total_reward = 0
        done = False

        state_memory = []
        reward_memory = []

        for _ in range(len(env.data)):
            state_tensor = torch.FloatTensor(state).to(device).half()

            with torch.no_grad():
                action = torch.argmax(model(state_tensor)).item()

            next_state, reward, done, _ = env.step(action)
            state_memory.append(state)
            reward_memory.append(reward)

            if len(state_memory) >= n_step:
                n_step_reward = sum([reward_memory[i] * (gamma ** i) for i in range(n_step)])
                buffer.add((state_memory[0], action, n_step_reward, next_state, done), error=1.0)
                state_memory.pop(0)
                reward_memory.pop(0)

            state = next_state
            total_reward += reward

            if done:
                break

            # ✅ 경험 재생 + Prioritized Replay 적용
            if len(buffer.buffer) >= batch_size:
                batch, indices = buffer.sample(batch_size)
                states, actions, rewards, next_states, dones = zip(*batch)

                states = torch.FloatTensor(np.array(states)).to(device).half()
                actions = torch.LongTensor(actions).to(device)
                rewards = torch.FloatTensor(rewards).to(device).half()
                next_states = torch.FloatTensor(np.array(next_states)).to(device).half()
                dones = torch.FloatTensor(dones).to(device)

                # Double DQN 적용
                current_q = model(states).gather(1, actions.unsqueeze(1)).squeeze(1)
                next_q = target_model(next_states).gather(1, model(next_states).argmax(dim=1, keepdim=True)).squeeze(1)
                target_q = rewards + gamma_n * next_q * (1 - dones)

                loss = loss_fn(current_q, target_q)
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()

                errors = (current_q - target_q).detach().cpu().numpy()
                buffer.update_priorities(indices, errors)

        # ✅ Target Network 업데이트 주기 증가 (1000 스텝마다)
        if episode % 10 == 0:
            target_model.load_state_dict(model.state_dict())

        episode_time = time.time() - episode_start
        total_elapsed = time.time() - start_time
        print(f"Episode {episode}, Total Reward: {total_reward:.2f}, Time: {episode_time:.2f}s, Total Elapsed: {total_elapsed:.2f}s")

    print(f"✅ 전체 학습 완료! 총 소요 시간: {time.time() - start_time:.2f}초")
    return model

# ✅ 6️⃣ 데이터 로드 및 환경 설정
data = pd.read_csv("marine_data.csv")
env = MarineDebrisEnv(data)

# ✅ 7️⃣ 모델 학습 실행
trained_model = train_dqn(env)
