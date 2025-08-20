import pygame
from pygame.locals import *
import math

pygame.init()

# Constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
TILE_SIZE = 32
FPS = 60

# Enhanced color palette (NES-inspired)
SKY = (92, 148, 252)
GROUND = (193, 97, 0)
BRICK = (181, 49, 32)
PIPE = (0, 168, 0)
CASTLE_GRAY = (150, 150, 150)
LAVA_RED = (252, 0, 0)
UNDERGROUND = (0, 0, 0)
COIN_YELLOW = (252, 188, 60)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

class Camera:
    def __init__(self, width, height):
        self.rect = pygame.Rect(0, 0, width, height)
        self.width = width
        self.height = height

    def apply(self, entity):
        return entity.rect.move(-self.rect.x, -self.rect.y)

    def update(self, target):
        x = target.rect.centerx - SCREEN_WIDTH // 2
        x = max(0, min(x, self.width - SCREEN_WIDTH))
        self.rect.x = x

class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.width = 24
        self.height = 32
        self.image = pygame.Surface((self.width, self.height))
        self.image.fill((255, 0, 0))  # Mario red
        pygame.draw.rect(self.image, (0, 0, 255), (0, 16, self.width, 16))  # Blue overalls
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        self.vel_x = 0
        self.vel_y = 0
        self.on_ground = False
        self.jump_power = -15
        self.max_speed = 6
        self.acceleration = 0.5
        self.friction = 0.4
        self.gravity = 0.8
        self.facing_right = True
        self.lives = 3
        self.invincible = 0
        self.power_up = 0  # 0=small, 1=big, 2=fire

    def update(self):
        # Apply gravity
        self.vel_y += self.gravity
        if self.vel_y > 20:
            self.vel_y = 20
        
        # Apply friction
        if self.vel_x > 0:
            self.vel_x -= self.friction
            if self.vel_x < 0:
                self.vel_x = 0
        elif self.vel_x < 0:
            self.vel_x += self.friction
            if self.vel_x > 0:
                self.vel_x = 0
        
        # Update position
        self.rect.x += self.vel_x
        self.rect.y += self.vel_y
        
        # Handle invincibility frames
        if self.invincible > 0:
            self.invincible -= 1

    def jump(self):
        if self.on_ground:
            self.vel_y = self.jump_power
            self.on_ground = False

    def move_left(self):
        self.vel_x = max(-self.max_speed, self.vel_x - self.acceleration)
        self.facing_right = False

    def move_right(self):
        self.vel_x = min(self.max_speed, self.vel_x + self.acceleration)
        self.facing_right = True

class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y, enemy_type='goomba'):
        super().__init__()
        self.enemy_type = enemy_type
        self.width = 24
        self.height = 24
        
        if enemy_type == 'goomba':
            self.image = pygame.Surface((self.width, self.height))
            self.image.fill((139, 69, 19))
        elif enemy_type == 'koopa':
            self.image = pygame.Surface((self.width, 32))
            self.image.fill((0, 200, 0))
            self.height = 32
        elif enemy_type == 'piranha':
            self.image = pygame.Surface((self.width, 32))
            self.image.fill((0, 255, 0))
            self.height = 32
        elif enemy_type == 'bowser':
            self.width = 48
            self.height = 48
            self.image = pygame.Surface((self.width, self.height))
            self.image.fill((255, 0, 0))
        
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        self.vel_x = -2 if enemy_type != 'piranha' else 0
        self.vel_y = 0
        self.on_ground = False

    def update(self):
        if self.enemy_type != 'piranha':
            self.rect.x += self.vel_x
            self.vel_y += 0.8
            if self.vel_y > 15:
                self.vel_y = 15
            self.rect.y += self.vel_y

class Platform(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height, platform_type='ground'):
        super().__init__()
        self.platform_type = platform_type
        self.image = pygame.Surface((width, height))
        
        if platform_type == 'ground':
            self.image.fill(GROUND)
        elif platform_type == 'brick':
            self.image.fill(BRICK)
        elif platform_type == 'pipe':
            self.image.fill(PIPE)
        elif platform_type == 'castle':
            self.image.fill(CASTLE_GRAY)
        elif platform_type == 'lava':
            self.image.fill(LAVA_RED)
        elif platform_type == 'question':
            self.image.fill((255, 200, 0))
            pygame.draw.rect(self.image, BLACK, (width//3, height//3, width//3, height//3))
        
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        self.breakable = platform_type == 'brick'
        self.has_item = platform_type == 'question'

class Coin(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((20, 20))
        pygame.draw.circle(self.image, COIN_YELLOW, (10, 10), 10)
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y

class Flag(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((50, 200), pygame.SRCALPHA)
        # Draw flagpole
        pygame.draw.rect(self.image, (100, 100, 100), (0, 0, 10, 200))
        # Draw flag (triangular)
        pygame.draw.polygon(self.image, (0, 255, 0), [(10, 20), (45, 35), (10, 50)])
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y

# Level definitions - 32 levels inspired by SMB1
def generate_level(world, level):
    """Generate level layout based on world and level number"""
    platforms = pygame.sprite.Group()
    enemies = pygame.sprite.Group()
    coins = pygame.sprite.Group()
    items = pygame.sprite.Group()
    
    level_width = 30 * TILE_SIZE  # Base level width
    
    # Always create a flag at the end of the level
    flag = Flag(level_width - 2 * TILE_SIZE, SCREEN_HEIGHT - TILE_SIZE * 8)
    
    # Ground for all levels
    for x in range(0, level_width, TILE_SIZE):
        if x < level_width - 5 * TILE_SIZE:  # Leave gap before flag
            ground = Platform(x, SCREEN_HEIGHT - TILE_SIZE * 2, TILE_SIZE, TILE_SIZE * 2, 'ground')
            platforms.add(ground)
    
    # Add flag platform
    flag_platform = Platform(level_width - 3 * TILE_SIZE, SCREEN_HEIGHT - TILE_SIZE * 2, 
                            TILE_SIZE * 3, TILE_SIZE * 2, 'ground')
    platforms.add(flag_platform)
    
    # World-specific theming
    if world == 1:  # Overworld
        # Add pipes
        for i in range(3, 20, 7):
            pipe = Platform(i * TILE_SIZE, SCREEN_HEIGHT - TILE_SIZE * 4, 
                          TILE_SIZE * 2, TILE_SIZE * 2, 'pipe')
            platforms.add(pipe)
            
            # Add piranha plants in some pipes
            if i % 2 == 0:
                enemy = Enemy(i * TILE_SIZE + TILE_SIZE//2, SCREEN_HEIGHT - TILE_SIZE * 5, 'piranha')
                enemies.add(enemy)
        
        # Add question blocks and bricks
        for i in range(5, 25, 4):
            height = SCREEN_HEIGHT - TILE_SIZE * (5 + (i % 3))
            if i % 2 == 0:
                block = Platform(i * TILE_SIZE, height, TILE_SIZE, TILE_SIZE, 'question')
            else:
                block = Platform(i * TILE_SIZE, height, TILE_SIZE, TILE_SIZE, 'brick')
            platforms.add(block)
            
            # Add coins above some blocks
            if i % 3 == 0:
                coin = Coin(i * TILE_SIZE + 6, height - TILE_SIZE)
                coins.add(coin)
        
        # Add goombas
        for i in range(4, 20, 5):
            enemy = Enemy(i * TILE_SIZE, SCREEN_HEIGHT - TILE_SIZE * 3, 'goomba')
            enemies.add(enemy)
    
    elif world == 2:  # Underground
        # Create underground ceiling
        for x in range(0, level_width, TILE_SIZE):
            ceiling = Platform(x, 0, TILE_SIZE, TILE_SIZE * 2, 'brick')
            platforms.add(ceiling)
        
        # Add platforms
        for i in range(3, 20, 3):
            platform = Platform(i * TILE_SIZE, SCREEN_HEIGHT - TILE_SIZE * (4 + i % 3), 
                              TILE_SIZE * 3, TILE_SIZE, 'brick')
            platforms.add(platform)
            
            # Add coins on platforms
            for j in range(3):
                coin = Coin(i * TILE_SIZE + j * TILE_SIZE + 6, 
                          SCREEN_HEIGHT - TILE_SIZE * (5 + i % 3))
                coins.add(coin)
        
        # Add koopa troopas
        for i in range(5, 20, 6):
            enemy = Enemy(i * TILE_SIZE, SCREEN_HEIGHT - TILE_SIZE * 3, 'koopa')
            enemies.add(enemy)
    
    elif world == 3:  # Athletic/Sky
        # Create floating platforms
        for i in range(2, 25, 2):
            y_offset = math.sin(i * 0.5) * 3
            platform = Platform(i * TILE_SIZE, 
                              SCREEN_HEIGHT - TILE_SIZE * (3 + int(y_offset)), 
                              TILE_SIZE * 2, TILE_SIZE, 'brick')
            platforms.add(platform)
            
            # Add coins between platforms
            if i % 4 == 0:
                for j in range(3):
                    coin = Coin(i * TILE_SIZE + j * 20, 
                              SCREEN_HEIGHT - TILE_SIZE * (5 + int(y_offset)))
                    coins.add(coin)
        
        # Flying koopas
        for i in range(4, 20, 8):
            enemy = Enemy(i * TILE_SIZE, SCREEN_HEIGHT - TILE_SIZE * 6, 'koopa')
            enemies.add(enemy)
    
    elif world == 4:  # Castle
        # Lava pits
        for i in range(5, 25, 5):
            lava = Platform(i * TILE_SIZE, SCREEN_HEIGHT - TILE_SIZE, 
                          TILE_SIZE * 2, TILE_SIZE, 'lava')
            platforms.add(lava)
        
        # Castle blocks
        for i in range(3, 25, 3):
            block = Platform(i * TILE_SIZE, SCREEN_HEIGHT - TILE_SIZE * 4, 
                           TILE_SIZE * 2, TILE_SIZE, 'castle')
            platforms.add(block)
        
        # Add Bowser at the end of castle levels
        if level == 4:
            boss = Enemy(level_width - 5 * TILE_SIZE, SCREEN_HEIGHT - TILE_SIZE * 4, 'bowser')
            enemies.add(boss)
        else:
            # Regular enemies for non-boss castle levels
            for i in range(4, 20, 4):
                enemy = Enemy(i * TILE_SIZE, SCREEN_HEIGHT - TILE_SIZE * 3, 'goomba')
                enemies.add(enemy)
    
    elif world == 5:  # Water world (simplified as platforms over water)
        # Water platforms
        for i in range(2, 25, 3):
            platform = Platform(i * TILE_SIZE, SCREEN_HEIGHT - TILE_SIZE * 3, 
                              TILE_SIZE * 3, TILE_SIZE, 'brick')
            platforms.add(platform)
            
            # Coins above water
            coin = Coin(i * TILE_SIZE + TILE_SIZE, SCREEN_HEIGHT - TILE_SIZE * 4)
            coins.add(coin)
        
        # Swimming enemies (represented as jumping koopas)
        for i in range(6, 20, 5):
            enemy = Enemy(i * TILE_SIZE, SCREEN_HEIGHT - TILE_SIZE * 4, 'koopa')
            enemies.add(enemy)
    
    elif world == 6:  # Ice world
        # Slippery platforms
        for i in range(3, 25, 4):
            platform = Platform(i * TILE_SIZE, SCREEN_HEIGHT - TILE_SIZE * 4, 
                              TILE_SIZE * 4, TILE_SIZE, 'brick')
            platforms.add(platform)
        
        # Add enemies
        for i in range(5, 20, 6):
            enemy = Enemy(i * TILE_SIZE, SCREEN_HEIGHT - TILE_SIZE * 3, 'koopa')
            enemies.add(enemy)
    
    elif world == 7:  # Pipe world
        # Many pipes of varying heights
        for i in range(2, 25, 2):
            height = 2 + (i % 4)
            pipe = Platform(i * TILE_SIZE, SCREEN_HEIGHT - TILE_SIZE * (height + 2), 
                          TILE_SIZE * 2, TILE_SIZE * height, 'pipe')
            platforms.add(pipe)
            
            # Piranha plants in pipes
            if i % 3 == 0:
                enemy = Enemy(i * TILE_SIZE + TILE_SIZE//2, 
                            SCREEN_HEIGHT - TILE_SIZE * (height + 3), 'piranha')
                enemies.add(enemy)
    
    elif world == 8:  # Final world - combination of all challenges
        # Mixed platform types
        for i in range(2, 25):
            if i % 5 == 0:
                # Lava pit
                lava = Platform(i * TILE_SIZE, SCREEN_HEIGHT - TILE_SIZE, 
                              TILE_SIZE, TILE_SIZE, 'lava')
                platforms.add(lava)
            elif i % 3 == 0:
                # Floating platform
                platform = Platform(i * TILE_SIZE, SCREEN_HEIGHT - TILE_SIZE * 5, 
                                  TILE_SIZE * 2, TILE_SIZE, 'castle')
                platforms.add(platform)
            elif i % 2 == 0:
                # Question block
                block = Platform(i * TILE_SIZE, SCREEN_HEIGHT - TILE_SIZE * 4, 
                               TILE_SIZE, TILE_SIZE, 'question')
                platforms.add(block)
        
        # Multiple enemy types
        for i in range(3, 20, 3):
            if i % 6 == 0:
                enemy = Enemy(i * TILE_SIZE, SCREEN_HEIGHT - TILE_SIZE * 3, 'koopa')
            else:
                enemy = Enemy(i * TILE_SIZE, SCREEN_HEIGHT - TILE_SIZE * 3, 'goomba')
            enemies.add(enemy)
        
        # Final Bowser
        if level == 4:
            boss = Enemy(level_width - 5 * TILE_SIZE, SCREEN_HEIGHT - TILE_SIZE * 4, 'bowser')
            enemies.add(boss)
    
    return platforms, enemies, coins, items, flag, level_width

class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption('Super Mario Bros - 32 Levels')
        self.clock = pygame.time.Clock()
        self.running = True
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        
        # Game state
        self.current_world = 1
        self.current_level = 1
        self.score = 0
        self.coins_collected = 0
        self.time_limit = 400
        self.timer = self.time_limit
        self.level_completed = False  # Prevent multiple completions
        
        # Sprite groups
        self.all_sprites = pygame.sprite.Group()
        self.platforms = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        self.coins = pygame.sprite.Group()
        self.items = pygame.sprite.Group()
        
        # Initialize player and flag references
        self.player = None
        self.flag = None
        
        # Initialize level
        self.load_level()
    
    def load_level(self):
        # Clear all sprites
        self.all_sprites.empty()
        self.platforms.empty()
        self.enemies.empty()
        self.coins.empty()
        self.items.empty()
        
        # Generate level
        platforms, enemies, coins, items, flag, level_width = generate_level(
            self.current_world, self.current_level
        )
        
        # Add sprites to groups
        self.platforms = platforms
        self.enemies = enemies
        self.coins = coins
        self.items = items
        self.flag = flag  # Store flag reference
        
        # Add all to main sprite group
        self.all_sprites.add(platforms)
        self.all_sprites.add(enemies)
        self.all_sprites.add(coins)
        self.all_sprites.add(items)
        self.all_sprites.add(self.flag)  # Always add flag
        
        # Create player
        self.player = Player(TILE_SIZE * 2, SCREEN_HEIGHT - TILE_SIZE * 4)
        self.all_sprites.add(self.player)
        
        # Setup camera
        self.camera = Camera(level_width, SCREEN_HEIGHT)
        
        # Reset timer
        self.timer = self.time_limit
    
    def handle_collisions(self):
        # Player-platform collisions
        hits = pygame.sprite.spritecollide(self.player, self.platforms, False)
        for hit in hits:
            if hit.platform_type == 'lava':
                self.player_death()
                return
            
            if self.player.vel_y > 0:  # Falling down
                if self.player.rect.bottom > hit.rect.top:
                    self.player.rect.bottom = hit.rect.top
                    self.player.vel_y = 0
                    self.player.on_ground = True
            elif self.player.vel_y < 0:  # Jumping up
                if self.player.rect.top < hit.rect.bottom:
                    if hit.has_item:
                        # Release item from question block
                        hit.has_item = False
                        hit.image.fill(CASTLE_GRAY)
                        self.score = int(self.score + 100)
                        # Could add mushroom/flower here
                    elif hit.breakable and self.player.power_up > 0:
                        # Break brick
                        hit.kill()
                        self.score = int(self.score + 50)
                    self.player.rect.top = hit.rect.bottom
                    self.player.vel_y = 0
        
        # Enemy-platform collisions
        for enemy in self.enemies:
            hits = pygame.sprite.spritecollide(enemy, self.platforms, False)
            for hit in hits:
                if enemy.vel_y > 0:
                    enemy.rect.bottom = hit.rect.top
                    enemy.vel_y = 0
                    enemy.on_ground = True
        
        # Player-enemy collisions
        if self.player.invincible <= 0:
            enemy_hits = pygame.sprite.spritecollide(self.player, self.enemies, False)
            for enemy in enemy_hits:
                if self.player.vel_y > 0 and self.player.rect.bottom < enemy.rect.centery:
                    # Stomp enemy
                    enemy.kill()
                    self.score = int(self.score + 100)
                    self.player.vel_y = -10
                else:
                    # Take damage
                    if self.player.power_up > 0:
                        self.player.power_up -= 1
                        self.player.invincible = 120
                    else:
                        self.player_death()
        
        # Player-coin collisions
        coin_hits = pygame.sprite.spritecollide(self.player, self.coins, True)
        for coin in coin_hits:
            self.score = int(self.score + 10)
            self.coins_collected += 1
            if self.coins_collected >= 100:
                self.player.lives += 1
                self.coins_collected = 0
        
        # Player-flag collision
        if hasattr(self, 'flag') and self.flag is not None:
            if self.player.rect.colliderect(self.flag.rect):
                self.level_complete()
    
    def player_death(self):
        self.player.lives -= 1
        if self.player.lives <= 0:
            self.game_over()
        else:
            self.load_level()
    
    def level_complete(self):
        # Play a simple victory animation
        for i in range(30):  # Brief pause for victory
            # Process events to keep window responsive
            for event in pygame.event.get():
                if event.type == QUIT:
                    self.running = False
                    return
            
            self.clock.tick(FPS)
            # Draw victory frame
            if self.current_world == 2:
                self.screen.fill(BLACK)
            elif self.current_world == 3:
                self.screen.fill((135, 206, 235))
            elif self.current_world == 4 or self.current_world == 8:
                self.screen.fill((50, 50, 50))
            else:
                self.screen.fill(SKY)
            
            for sprite in self.all_sprites:
                self.screen.blit(sprite.image, self.camera.apply(sprite))
            
            # Show "LEVEL COMPLETE!" message
            complete_text = self.font.render("LEVEL COMPLETE!", True, COIN_YELLOW)
            self.screen.blit(complete_text, (SCREEN_WIDTH//2 - complete_text.get_width()//2, SCREEN_HEIGHT//2))
            pygame.display.flip()
        
        # Award time bonus
        self.score = int(self.score + int(self.timer) * 10)
        
        # Progress to next level
        self.current_level += 1
        if self.current_level > 4:
            self.current_level = 1
            self.current_world += 1
            if self.current_world > 8:
                self.game_complete()
                return
        
        self.load_level()
    
    def game_over(self):
        # Display game over screen
        self.screen.fill(BLACK)
        text = self.font.render("GAME OVER", True, WHITE)
        score_text = self.small_font.render(f"Final Score: {self.score}", True, WHITE)
        self.screen.blit(text, (SCREEN_WIDTH//2 - text.get_width()//2, SCREEN_HEIGHT//2 - 50))
        self.screen.blit(score_text, (SCREEN_WIDTH//2 - score_text.get_width()//2, SCREEN_HEIGHT//2))
        pygame.display.flip()
        pygame.time.wait(3000)
        self.__init__()  # Restart game
    
    def game_complete(self):
        # Display victory screen
        self.screen.fill(BLACK)
        text = self.font.render("CONGRATULATIONS!", True, COIN_YELLOW)
        text2 = self.font.render("YOU SAVED THE PRINCESS!", True, WHITE)
        score_text = self.small_font.render(f"Final Score: {self.score}", True, WHITE)
        self.screen.blit(text, (SCREEN_WIDTH//2 - text.get_width()//2, SCREEN_HEIGHT//2 - 100))
        self.screen.blit(text2, (SCREEN_WIDTH//2 - text2.get_width()//2, SCREEN_HEIGHT//2 - 50))
        self.screen.blit(score_text, (SCREEN_WIDTH//2 - score_text.get_width()//2, SCREEN_HEIGHT//2))
        pygame.display.flip()
        pygame.time.wait(5000)
        self.running = False
    
    def draw_hud(self):
        # Score
        score_text = self.small_font.render(f"SCORE: {int(self.score):06d}", True, WHITE)
        self.screen.blit(score_text, (10, 10))
        
        # Coins
        coin_text = self.small_font.render(f"COINS: {self.coins_collected:02d}", True, COIN_YELLOW)
        self.screen.blit(coin_text, (10, 40))
        
        # World-Level
        level_text = self.small_font.render(f"WORLD {self.current_world}-{self.current_level}", True, WHITE)
        self.screen.blit(level_text, (SCREEN_WIDTH//2 - 50, 10))
        
        # Timer
        timer_text = self.small_font.render(f"TIME: {int(self.timer)}", True, WHITE)
        self.screen.blit(timer_text, (SCREEN_WIDTH - 120, 10))
        
        # Lives
        lives_text = self.small_font.render(f"LIVES: {self.player.lives}", True, WHITE)
        self.screen.blit(lives_text, (SCREEN_WIDTH - 120, 40))
    
    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            
            # Handle events
            for event in pygame.event.get():
                if event.type == QUIT:
                    self.running = False
                elif event.type == KEYDOWN:
                    if event.key == K_SPACE or event.key == K_UP:
                        self.player.jump()
                    elif event.key == K_ESCAPE:
                        self.running = False
            
            # Handle continuous input
            keys = pygame.key.get_pressed()
            if keys[K_LEFT] or keys[K_a]:
                self.player.move_left()
            if keys[K_RIGHT] or keys[K_d]:
                self.player.move_right()
            if (keys[K_SPACE] or keys[K_UP] or keys[K_w]) and self.player.vel_y < -5:
                # Allow higher jumps by holding jump button
                self.player.vel_y -= 0.5
            
            # Update
            self.all_sprites.update()
            self.camera.update(self.player)
            self.handle_collisions()
            
            # Update timer
            self.timer -= dt
            if self.timer <= 0:
                self.player_death()
            
            # Draw
            if self.current_world == 2:  # Underground
                self.screen.fill(BLACK)
            elif self.current_world == 3:  # Sky
                self.screen.fill((135, 206, 235))  # Sky blue
            elif self.current_world == 4 or self.current_world == 8:  # Castle
                self.screen.fill((50, 50, 50))  # Dark gray
            else:
                self.screen.fill(SKY)
            
            # Draw all sprites with camera offset
            for sprite in self.all_sprites:
                self.screen.blit(sprite.image, self.camera.apply(sprite))
            
            # Draw HUD
            self.draw_hud()
            
            # Check if player fell off the map
            if self.player.rect.top > SCREEN_HEIGHT:
                self.player_death()
            
            # Prevent player from going too far past the level end
            if hasattr(self, 'camera') and self.player.rect.x > self.camera.width:
                self.player.rect.x = self.camera.width
            
            pygame.display.flip()
        
        pygame.quit()

if __name__ == "__main__":
    game = Game()
    game.run()
