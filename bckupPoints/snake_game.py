import pygame
import random
import sys

# Initialize pygame
pygame.init()

# Game constants
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
GRID_SIZE = 20
GRID_WIDTH = WINDOW_WIDTH // GRID_SIZE
GRID_HEIGHT = WINDOW_HEIGHT // GRID_SIZE

# Colors
BLACK = (0, 0, 0)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
WHITE = (255, 255, 255)

class Snake:
    def __init__(self):
        self.positions = [(GRID_WIDTH // 2, GRID_HEIGHT // 2)]
        self.direction = (1, 0)
        self.grow = False
    
    def move(self):
        head_x, head_y = self.positions[0]
        new_head = (head_x + self.direction[0], head_y + self.direction[1])
        
        # Check wall collision
        if (new_head[0] < 0 or new_head[0] >= GRID_WIDTH or 
            new_head[1] < 0 or new_head[1] >= GRID_HEIGHT):
            return False
        
        # Check self collision
        if new_head in self.positions:
            return False
        
        self.positions.insert(0, new_head)
        
        if not self.grow:
            self.positions.pop()
        else:
            self.grow = False
        
        return True
    
    def change_direction(self, direction):
        # Prevent moving in opposite direction
        if (direction[0] * -1, direction[1] * -1) != self.direction:
            self.direction = direction
    
    def eat_food(self):
        self.grow = True

class Food:
    def __init__(self):
        self.position = self.generate_position()
    
    def generate_position(self):
        return (random.randint(0, GRID_WIDTH - 1), random.randint(0, GRID_HEIGHT - 1))
    
    def respawn(self, snake_positions):
        while True:
            self.position = self.generate_position()
            if self.position not in snake_positions:
                break

def main():
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Snake Game - Use Arrow Keys or WASD")
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 36)
    
    snake = Snake()
    food = Food()
    score = 0
    
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            
            elif event.type == pygame.KEYDOWN:
                # Arrow keys
                if event.key == pygame.K_UP:
                    snake.change_direction((0, -1))
                elif event.key == pygame.K_DOWN:
                    snake.change_direction((0, 1))
                elif event.key == pygame.K_LEFT:
                    snake.change_direction((-1, 0))
                elif event.key == pygame.K_RIGHT:
                    snake.change_direction((1, 0))
                
                # WASD keys
                elif event.key == pygame.K_w:
                    snake.change_direction((0, -1))
                elif event.key == pygame.K_s:
                    snake.change_direction((0, 1))
                elif event.key == pygame.K_a:
                    snake.change_direction((-1, 0))
                elif event.key == pygame.K_d:
                    snake.change_direction((1, 0))
        
        # Move snake
        if not snake.move():
            # Game over
            game_over_text = font.render(f"Game Over! Score: {score}", True, WHITE)
            restart_text = font.render("Press any key to restart or close window to quit", True, WHITE)
            
            screen.fill(BLACK)
            screen.blit(game_over_text, (WINDOW_WIDTH // 2 - game_over_text.get_width() // 2, WINDOW_HEIGHT // 2 - 50))
            screen.blit(restart_text, (WINDOW_WIDTH // 2 - restart_text.get_width() // 2, WINDOW_HEIGHT // 2))
            pygame.display.flip()
            
            # Wait for restart
            waiting = True
            while waiting:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        sys.exit()
                    elif event.type == pygame.KEYDOWN:
                        # Restart game
                        snake = Snake()
                        food = Food()
                        score = 0
                        waiting = False
        
        # Check food collision
        if snake.positions[0] == food.position:
            snake.eat_food()
            food.respawn(snake.positions)
            score += 1
        
        # Draw everything
        screen.fill(BLACK)
        
        # Draw snake
        for position in snake.positions:
            rect = pygame.Rect(position[0] * GRID_SIZE, position[1] * GRID_SIZE, GRID_SIZE, GRID_SIZE)
            pygame.draw.rect(screen, GREEN, rect)
        
        # Draw food
        food_rect = pygame.Rect(food.position[0] * GRID_SIZE, food.position[1] * GRID_SIZE, GRID_SIZE, GRID_SIZE)
        pygame.draw.rect(screen, RED, food_rect)
        
        # Draw score
        score_text = font.render(f"Score: {score}", True, WHITE)
        screen.blit(score_text, (10, 10))
        
        pygame.display.flip()
        clock.tick(10)  # 10 FPS for smooth gameplay

if __name__ == "__main__":
    main()