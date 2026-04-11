#!/usr/bin/env python3
"""
Mock GPU cluster for load testing hub mode
Simulates realistic GPU workloads across multiple servers
"""

import time
import random
import asyncio
import json
from datetime import datetime
import argparse
import logging
from fastapi import FastAPI, WebSocket
import uvicorn

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)


# GPU profiles: (name, vram_mb, max_power_w, clock_base_range, vendor)
GPU_PROFILES = {
    'nvidia': [
        ('NVIDIA RTX 3080', 12288, 250, (1710, 1890), 'nvidia'),
        ('NVIDIA RTX 3090', 24576, 350, (1710, 1890), 'nvidia'),
        ('NVIDIA RTX 4090', 24576, 450, (2235, 2520), 'nvidia'),
        ('NVIDIA A100', 81920, 300, (1065, 1410), 'nvidia'),
    ],
    'amd': [
        ('AMD Radeon RX 7900 XTX', 24576, 355, (2000, 2500), 'amd'),
        ('AMD Radeon RX 7900 XT', 20480, 315, (1900, 2400), 'amd'),
        ('AMD Radeon RX 7800 XT', 16384, 263, (1800, 2430), 'amd'),
        ('AMD Instinct MI250X', 131072, 500, (1500, 1700), 'amd'),
    ],
}


class MockGPUNode:
    """Simulates a GPU node with realistic metrics for load testing"""

    def __init__(self, node_name, gpu_count, port=1312, vendor='nvidia'):
        self.node_name = node_name
        self.gpu_count = gpu_count
        self.port = port
        self.vendor = vendor
        self.app = FastAPI(title=f"Mock GPU Node {node_name}")
        self.websocket_connections = set()
        self.broadcasting = False

        profiles = GPU_PROFILES.get(vendor, GPU_PROFILES['nvidia'])

        # Initialize per-GPU state for realistic patterns
        self.gpu_states = []
        for gpu_id in range(gpu_count):
            profile = random.choice(profiles)
            gpu_name, mem_total, max_power, clock_range, gpu_vendor = profile
            is_busy = random.random() < 0.4
            self.gpu_states.append({
                'base_temp': random.randint(45, 55),
                'is_busy': is_busy,
                'job_start': time.time() - random.uniform(0, 300),
                'memory': mem_total,
                'max_power': max_power,
                'allocated_memory': mem_total * random.uniform(0.6, 0.92) if is_busy else 0,
                'clock_base': random.randint(*clock_range),
                'gpu_name': gpu_name,
                'vendor': gpu_vendor,
            })
        
        self.start_time = time.time()
        
    def _generate_realistic_utilization(self, state, timestamp):
        """Generate realistic ML training utilization patterns"""
        if not state['is_busy']:
            # Idle GPU - occasionally switch to busy
            if random.random() < 0.001:  # 0.1% chance per update to start job
                state['is_busy'] = True
                state['job_start'] = timestamp
                state['allocated_memory'] = state['memory'] * random.uniform(0.85, 0.95)
            return random.uniform(0, 3)
        
        # Busy GPU - simulate training epoch pattern
        job_duration = timestamp - state['job_start']
        epoch_time = 120  # 2 minute epochs
        epoch_progress = (job_duration % epoch_time) / epoch_time
        
        # Occasionally finish job
        if random.random() < 0.0005:  # Job finishes
            state['is_busy'] = False
            state['allocated_memory'] = 0
            return 0
        
        # Training pattern with data loading dips
        if epoch_progress < 0.05:  # Warmup phase
            return random.gauss(25, 5)
        elif epoch_progress > 0.93:  # Validation phase
            return random.gauss(65, 5)
        else:  # Main training
            base_util = random.gauss(96, 2)
            # Data loading dips every ~5 seconds
            if (timestamp % 5) < 0.4:
                base_util *= 0.75
            return max(0, min(100, base_util))
    
    def generate_gpu_data(self):
        """Generate realistic GPU metrics for load testing"""
        timestamp = time.time()
        gpus = {}
        processes = []
        
        for gpu_id in range(self.gpu_count):
            state = self.gpu_states[gpu_id]
            
            # Realistic utilization pattern
            util = self._generate_realistic_utilization(state, timestamp)
            
            # Memory: allocated at job start, stays constant during training
            if state['is_busy']:
                mem_used = state['allocated_memory'] + random.uniform(-20, 20)
            else:
                mem_used = random.uniform(200, 600)  # Driver/CUDA context overhead
            
            # Temperature: correlates with utilization, slow changes
            target_temp = state['base_temp'] + (util / 100) * 35
            temp_variation = random.gauss(0, 1)
            temp = max(30, min(92, target_temp + temp_variation))

            # Power: correlates with utilization
            max_power = state['max_power']
            power = (util / 100) * max_power * random.uniform(0.85, 1.0)

            # Clock speeds: stable based on load
            if util > 50:
                clock_graphics = state['clock_base'] + random.randint(-20, 20)
                pstate = 'P0'
            elif util > 10:
                clock_graphics = int(state['clock_base'] * 0.8) + random.randint(-15, 15)
                pstate = 'P2'
            else:
                clock_graphics = random.randint(210, 500)
                pstate = 'P8'

            gpu_entry = {
                'index': gpu_id,
                'name': state['gpu_name'],
                'vendor': state['vendor'],
                'utilization': round(util, 1),
                'temperature': round(temp, 1),
                'memory_used': round(mem_used, 0),
                'memory_total': state['memory'],
                'power_draw': round(power, 1),
                'power_limit': max_power,
                'fan_speed': round(min(100, 30 + max(0, temp - 40) * 1.5)),
                'clock_graphics': clock_graphics,
                'clock_memory': 9501 if state['memory'] >= 24576 else 9001,
                'pcie_gen': 4,
                'pcie_width': 16,
                'pstate': pstate,
                'throttle_reasons': []
            }

            # NVIDIA-specific fields
            if state['vendor'] == 'nvidia':
                gpu_entry['clock_sm'] = clock_graphics
                gpu_entry['encoder_sessions'] = 0
                gpu_entry['decoder_sessions'] = 0

            gpus[str(gpu_id)] = gpu_entry
            
            # Add processes for busy GPUs
            if state['is_busy']:
                process_count = random.randint(1, 2)
                for p in range(process_count):
                    processes.append({
                        'pid': random.randint(1000, 99999),
                        'name': random.choice(['python3', 'train.py', 'pytorch', 'python']),
                        'gpu_memory': round(mem_used / process_count, 0),
                        'gpu_id': gpu_id
                    })
        
        # System metrics: correlate with GPU load
        avg_gpu_util = sum(g['utilization'] for g in gpus.values()) / len(gpus)
        system = {
            'cpu_percent': round(random.gauss(15 + avg_gpu_util * 0.3, 5), 1),
            'memory_percent': round(random.gauss(60, 10), 1),
            'memory_used': round(random.gauss(80, 15), 1),
            'memory_total': 128.0
        }
        
        return {
            'node_name': self.node_name,
            'gpus': gpus,
            'processes': processes,
            'system': system
        }
    
    async def _broadcast_loop(self):
        """Background task to broadcast GPU data every 0.5s"""
        while self.broadcasting:
            try:
                data = self.generate_gpu_data()
                
                # Send to all connected clients
                if self.websocket_connections:
                    disconnected = set()
                    for websocket in self.websocket_connections:
                        try:
                            await websocket.send_text(json.dumps(data))
                        except:
                            disconnected.add(websocket)
                    
                    # Remove disconnected clients
                    self.websocket_connections -= disconnected
                    
            except Exception as e:
                logger.error(f'[{self.node_name}] Error in broadcast loop: {e}')
            await asyncio.sleep(0.5)
    
    def setup_routes(self):
        """Setup WebSocket routes"""
        
        @self.app.websocket("/socket.io/")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            self.websocket_connections.add(websocket)
            logger.info(f'[{self.node_name}] Client connected')
            
            # Start broadcasting when first client connects
            if not self.broadcasting:
                self.broadcasting = True
                asyncio.create_task(self._broadcast_loop())
            
            try:
                # Keep connection alive
                while True:
                    await websocket.receive_text()
            except Exception as e:
                logger.debug(f'[{self.node_name}] Client disconnected: {e}')
            finally:
                self.websocket_connections.discard(websocket)
    
    async def run(self):
        """Run the mock node server"""
        self.setup_routes()
        
        logger.info(f'[{self.node_name}] Starting mock node with {self.gpu_count} GPUs on port {self.port}')
        
        # Create server config
        config = uvicorn.Config(
            self.app, 
            host='0.0.0.0', 
            port=self.port, 
            log_level='info',
            access_log=False
        )
        server = uvicorn.Server(config)
        await server.serve()


async def start_mock_node(node_name, gpu_count, port, vendor='nvidia'):
    """Start a mock node as async task"""
    node = MockGPUNode(node_name, gpu_count, port, vendor=vendor)
    await node.run()


async def main():
    parser = argparse.ArgumentParser(description='Mock GPU cluster for testing')
    parser.add_argument('--nodes', type=str, default='2,4,8',
                      help='Comma-separated GPU counts for each node (e.g., "2,4,8")')
    parser.add_argument('--base-port', type=int, default=13120,
                      help='Base port for nodes (increments for each node)')
    parser.add_argument('--prefix', type=str, default='gpu-server',
                      help='Prefix for node names')
    parser.add_argument('--vendors', type=str, default=None,
                      help='Comma-separated vendor per node: nvidia or amd (e.g., "nvidia,amd,nvidia"). '
                           'Defaults to all nvidia. Use "mixed" to auto-assign alternating vendors.')

    args = parser.parse_args()

    gpu_counts = [int(x.strip()) for x in args.nodes.split(',')]

    # Resolve vendor per node
    if args.vendors is None:
        vendors = ['nvidia'] * len(gpu_counts)
    elif args.vendors == 'mixed':
        vendors = ['nvidia' if i % 2 == 0 else 'amd' for i in range(len(gpu_counts))]
    else:
        vendors = [v.strip() for v in args.vendors.split(',')]
        # Pad with last value if fewer vendors than nodes
        while len(vendors) < len(gpu_counts):
            vendors.append(vendors[-1])

    print("\n" + "="*60)
    print("GPU Hot - Mock Cluster Test (FastAPI + AsyncIO)")
    print("="*60)
    print(f"\nStarting {len(gpu_counts)} mock GPU servers:\n")

    node_urls = []
    for i, gpu_count in enumerate(gpu_counts):
        port = args.base_port + i
        node_name = f"{args.prefix}-{i+1}"
        vendor = vendors[i]
        node_urls.append(f"http://localhost:{port}")
        print(f"  • {node_name}: {gpu_count} {vendor.upper()} GPUs on port {port}")

    print("\n" + "-"*60)
    print("Mock nodes running! Now start the hub with:")
    print("-"*60)
    print(f"\nexport GPU_HOT_MODE=hub")
    print(f"export NODE_URLS={','.join(node_urls)}")
    print(f"python app.py")
    print("\nOr with Docker:")
    print(f"\ndocker run -d -p 1312:1312 \\")
    print(f"  -e GPU_HOT_MODE=hub \\")
    print(f"  -e NODE_URLS={','.join(node_urls)} \\")
    print(f"  --network=host \\")
    print(f"  ghcr.io/psalias2006/gpu-hot:latest")
    print("\nThen open: http://localhost:1312")
    print("-"*60 + "\n")

    # Start all nodes concurrently
    tasks = []
    for i, gpu_count in enumerate(gpu_counts):
        port = args.base_port + i
        node_name = f"{args.prefix}-{i+1}"
        vendor = vendors[i]
        task = asyncio.create_task(start_mock_node(node_name, gpu_count, port, vendor))
        tasks.append(task)

    # Keep all tasks running
    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        print("\n\nStopping mock cluster...")


if __name__ == '__main__':
    asyncio.run(main())

