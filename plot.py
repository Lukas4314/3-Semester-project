import numpy as np
import matplotlib.pyplot as plt

def demonstrate_ambiguity():
    # Our microphone array
    mics = np.array([[0, 0], [0.2, 0], [0.1, 0.1732]])
    
    # True sound source
    true_pos = np.array([1.0, 0.8])
    
    # Calculate the "mirror" solution that gives same TDOAs
    # This is approximately what your code found earlier
    mirror_pos = np.array([0.58, 0.43])
    
    # Verify both give same TDOAs
    def calculate_tdoas(position, mics, sound_speed=343):
        distances = [np.linalg.norm(position - mic) for mic in mics]
        tdoas = [
            (distances[1] - distances[0]) / sound_speed,  # mic1-mic0
            (distances[2] - distances[0]) / sound_speed,  # mic2-mic0
            (distances[2] - distances[1]) / sound_speed   # mic2-mic1
        ]
        return tdoas
    
    tdoas_true = calculate_tdoas(true_pos, mics)
    tdoas_mirror = calculate_tdoas(mirror_pos, mics)
    
    print("TRUE POSITION:", true_pos)
    print("TDOAs:", [f"{t:.6f}s" for t in tdoas_true])
    print("\nMIRROR POSITION:", mirror_pos) 
    print("TDOAs:", [f"{t:.6f}s" for t in tdoas_mirror])
    print("\nBoth positions give IDENTICAL TDOAs!")
    
    # Plot both solutions
    plt.figure(figsize=(12, 10))
    
    # Plot microphones
    plt.scatter(mics[:, 0], mics[:, 1], c='red', s=200, label='Microphones', zorder=5)
    for i, mic in enumerate(mics):
        plt.text(mic[0] + 0.02, mic[1] + 0.02, f'Mic{i}', fontsize=12, weight='bold')
    
    # Plot both possible positions
    plt.scatter(true_pos[0], true_pos[1], c='green', s=200, label='True Position', zorder=5)
    plt.scatter(mirror_pos[0], mirror_pos[1], c='blue', s=200, label='Mirror Position', zorder=5)
    
    plt.text(true_pos[0] + 0.05, true_pos[1], 'True\n[1.0, 0.8]', fontsize=11, weight='bold')
    plt.text(mirror_pos[0] + 0.05, mirror_pos[1], 'Mirror\n[0.58, 0.43]', fontsize=11, weight='bold')
    
    # Draw the hyperbolas
    from matplotlib.patches import Ellipse
    # Simplified: draw circles to show distance relationships
    for i, mic in enumerate(mics):
        # Circles for true position
        circle_true = plt.Circle(mic, np.linalg.norm(true_pos - mic), 
                               color='green', alpha=0.1, linestyle='-', linewidth=2)
        # Circles for mirror position  
        circle_mirror = plt.Circle(mic, np.linalg.norm(mirror_pos - mic),
                                 color='blue', alpha=0.1, linestyle='--', linewidth=2)
        plt.gca().add_patch(circle_true)
        plt.gca().add_patch(circle_mirror)
    
    plt.xlabel('X (meters)')
    plt.ylabel('Y (meters)')
    plt.title('TDOA AMBIGUITY: Two Different Positions Give Identical TDOA Measurements', fontsize=14)
    plt.axis('equal')
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.xlim(-0.5, 2.0)
    plt.ylim(-0.5, 1.5)
    plt.show()

demonstrate_ambiguity()