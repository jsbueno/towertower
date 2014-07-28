# coding: utf-8

import random
from random import randint
import pygame
from pygame.locals import *

SIZE = 800,600
FLAGS = 0
# actually, delay in ms:
FRAMERATE = 30

Group = pygame.sprite.OrderedUpdates

class GameOver(Exception):
    pass


class Vector(object):
    def __init__(self, x=0, y=0):
        if hasattr(x, "__len__"):
            self.x = x[0]
            self.y = x[1]
        else:
            self.x = x
            self.y = y
 
    def __getitem__(self, index):
        if index == 0:
            return self.x
        return self.y
     
    def __len__(self):
        return 2
     
    def __add__(self, other):
        return Vector(self[0] + other[0], self[1] + other[1])
     
    def __sub__(self, other):
        return Vector(self[0] - other[0], self[1] - other[1])
     
    def size(self):
        return (self[0] ** 2 + self[1] ** 2) ** 0.5
     
    def distance(self, other):
        return (self - other).size()
         
    def __repr__(self):
        return "Vector({}, {})".format(self.x, self.y)
    
    def __eq__(self, other):
        return self[0] == other[0] and self[1] == other[1]

def draw_bg(surface, rect=None):
    if rect is None:
        surface.fill((0,0,0))
    pygame.draw.rect(surface, (0,0,0), rect)

class BaseTowerObject(pygame.sprite.Sprite):
    size = 20
    color = (255,255,255)
    def __init__(self, map_, position=Vector((0,0))):
        super(BaseTowerObject, self).__init__()
        self.map_ = map_
        self.image = pygame.surface.Surface((self.size, self.size))
        self.image.fill(self.color)
        self.position = position
        self.rect = pygame.Rect((0,0,self.size, self.size))
        self.rect.center = position


class Targetting(BaseTowerObject):
    def update(self):
        super(Targetting, self).update()
        objective = self.objective
        if not objective:
            return
        for i in range(self.speed):
            if objective.position.x < self.position.x:
                self.position.x -= 1
            elif objective.position.x > self.position.x:
                self.position.x += 1
            if objective.position.y < self.position.y:
                self.position.y -= 1
            elif  objective.position.y > self.position.y:
                self.position.y += 1
        self.rect.center = self.position
    
class Enemy(Targetting):
    speed = 1
    size = 15
    color = (255, 0, 0)
    
    speed = 1
    endurance = 5
    
    def __init__(self, map_, position):
        super(Enemy, self).__init__(map_, position)
        self.speed = self.__class__.speed
        self.stamina = self.__class__.endurance
        
    def update(self):
        self.objective = iter(self.map_.objective).next()
        super(Enemy, self).update()
        if self.position == self.objective.position:
            self.objective.enemies_reached.add(self)


class Tower(BaseTowerObject):
    size = 15
    color = (0, 0, 255)
    
    repeat_rate = 15
    def __init__(self, *args):
        super(Tower, self).__init__(*args)
        self.last_shot = self.repeat_rate

    def update(self):
        super(Tower, self).update()
        self.last_shot -= 1
        if self.last_shot <= 0:
            self.last_shot = self.repeat_rate
            self.shoot()
    
    def shoot(self):
        self.map_.shots.add(Shoot(self.map_, Vector(self.position)))

class Shoot(Targetting):
    size = 3
    color = (0, 255, 0)
    speed = 2
    range_ = 100
    
    def __init__(self, *args):
        super(Shoot, self).__init__(*args)
        self.start_pos = self.position
        self.objective = self.get_closer_enemy()
        
    def get_closer_enemy(self):
        distance = max(SIZE) * 2
        closest = None
        for enemy in self.map_.enemies:
            if self.position.distance(enemy.position) < distance:
                closest = enemy
                distance = self.position.distance(enemy.position)
        return closest
    
    def update(self):
        if not self.objective:
            self.kill()
            return
        
        super(Shoot, self).update()
        
        if (self.position.distance(self.objective.position) < self.size / 2.0):
            # self.objective.clear()
            self.objective.kill()
            self.objective = None
            self.kill()
        if self.position.distance(self.start_pos) > self.range_:
            self.kill()
            
class Objective(BaseTowerObject):
    color = (255,255,0)
    lives = 5
    
    def __init__(self, map_, position):
        super(Objective, self).__init__(map_, position)
        self.enemies_reached = set() # not pygame.sprite.Group(), because in the alpha
                                     # implementation, enemies here are the count to 
                                     # indicate map defeat. And killing the enemies
                                     # would remove then from a Group
        
    def update(self):
        super(Objective, self).update()
        if len(self.enemies_reached) > self.lives:
            raise GameOver
        
class Map(object):
    def __init__(self):
        self.enemies = Group()
        self.towers = Group()
        self.shots = Group()
        self.objective = Group()

    
def user_iteration(map_):
    pygame.event.pump()
    for event in pygame.event.get():
        if event.type == MOUSEBUTTONDOWN:
            map_.towers.add(Tower(map_, Vector(event.pos)))
        elif event.type == KEYDOWN and event.key == K_ESCAPE:
            raise GameOver
        
def iteration(map_):
    global screen
    object_types = "enemies towers shots objective"
    user_iteration(map_)
    for group in (getattr(map_, type_) for type_ in object_types.split()):
        group.clear(screen, draw_bg)
        group.update()
        group.draw(screen)
    pygame.display.flip()
    pygame.time.delay(FRAMERATE)

def start_map(map_):
    obj = Objective(map_, Vector(randint(0, SIZE[0]), randint(0, SIZE[1])))
    map_.objective.add(obj)
    for i in range(50):
        enemy = Enemy(map_, 
                      Vector(randint(0, SIZE[0]), randint(0, SIZE[1])))
        map_.enemies.add(enemy)


def main():
    ticks = 0
    map_ = Map()
    start_map(map_)
    while True:
        try:
            iteration(map_)
        except GameOver:
            break
    
def init():
    global screen
    pygame.init()
    
    try:
        screen = pygame.display.set_mode(SIZE, FLAGS)
        main()
    finally:
        pygame.quit()

if __name__ == "__main__":
    init()

