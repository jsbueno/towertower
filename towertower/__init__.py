# coding: utf-8
from __future__ import division


import random
from random import randint
import pygame
from pygame.locals import *

SIZE = 800,600
FLAGS = 0
# actually, delay in ms:
FRAMERATE = 30


WAVE_ENEMIES = [1, 5, 1]

Group = pygame.sprite.OrderedUpdates

class GameOver(Exception):
    pass

class NoEnemyInRange(Exception):
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

    def __mul__(self, other):
        return Vector(self[0] * other, self[1] * other)
     
    def __div__(self, other):
        return Vector(self[0] / other, self[1] / other)

    __truediv__ = __div__


    def size(self):
        return (self[0] ** 2 + self[1] ** 2) ** 0.5
     
    def distance(self, other):
        return (self - other).size()
         
    def __repr__(self):
        return "Vector({}, {})".format(self.x, self.y)
    
    epsilon = 1
    def __eq__(self, other):
        return self.distance(other) < self.epsilon

    def normalize(self):
        size = self.size()
        if size == 0:
            return 0
        return self / size


class Event(object):
    def __init__(self, event_type, callback):
        self.type = event_type
        self.callback = callback

    def __call__(self, instance=None):
        self.callback(instance)

class EventQueue(object):
    def __init__(self):
        self._list = []

    def post(self, event):
        self._list.append(event)

    def pick(self, type_=None):
        for i, event in enumerate(self._list):
            if type_ is None or event.type == type_:
                del self._list[i]
                return event
        return None


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
        self.events = EventQueue()


class Targetting(BaseTowerObject):

    movement_type = "tracking"
    # possible_values: ("tracking", "straight")

    def update(self):
        super(Targetting, self).update()
        movement_function = getattr(self, self.movement_type)
        movement_function()

        self.rect.center = self.position

    def tracking(self):
        objective = self.objective if isinstance(self.objective, pygame.sprite.Sprite) else self.objective.sprites()[0]
        if not objective:
            return
        self.direction = (objective.position - self.position).normalize()
        return self._update(self.direction)

    def straight(self):
        if not hasattr(self, "direction"):
            objective = self.objective if isinstance(self.objective, pygame.sprite.Sprite) else self.objective.sprites()[0]
            target_position = Vector(objective.position)
            self.direction = (target_position - self.position).normalize()
        return self._update(self.direction)

    def _update(self, direction):
        self.position += direction * self.speed

    
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
            self.kill()

class StrongEnemy(Enemy):
    color = (255, 128, 0)
    size = 12
    endurance = 25

class FastEnemy(Enemy):
    color = (128,255,0)
    size = 18
    endurance = 3
    speed = 4

class Tower(BaseTowerObject):
    size = 15
    color = (0, 0, 255)
    shot_type = "Shot"

    repeat_rate = 15
    def __init__(self, *args):
        super(Tower, self).__init__(*args)
        if isinstance(self.shot_type, basestring):
            # TODO: create a game class registry from where to retrieve this
            self.shot_type = globals()[self.shot_type]
        self.last_shot = self.repeat_rate


    def update(self):
        super(Tower, self).update()
        self.last_shot -= 1
        if self.last_shot <= 0:
            self.last_shot = self.repeat_rate
            if self.shoot():
                event = self.events.pick("after_shot")
                if event: event(self)

    def shoot(self):
        try:
            self.map_.shots.add(self.shot_type(
                self.map_, Vector(self.position), piercing=getattr(self, "piercing", None)))
            return True
        except NoEnemyInRange:
            pass
        return False

class TeleTower(Tower):
    size = 15
    color = (0, 255, 128)
    shot_type = "TeleShot"


class Shot(Targetting):
    size = 3
    color = (0, 255, 0)
    speed = 5
    range_ = 800
    piercing = 2

    movement_type = "straight"

    def __init__(self, *args, **kw):
        super(Shot, self).__init__(*args)
        if kw.get("piercing", False):
            self.piercing = kw.pop("piercing")
        self.start_pos = self.position
        objective = self.get_closer_enemy()
        if objective and self.position.distance(objective.position) <= self.range_:
            self.objective = pygame.sprite.GroupSingle()
            self.objective.sprite = objective
        else:
            raise NoEnemyInRange

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

        super(Shot, self).update()

        shot_enemy = None
        for shot_enemy in pygame.sprite.spritecollide(self, self.map_.enemies, False):
            # No surprises in Python as long as we are using imutable objects
            # to keep data: the class "endurance" atribute
            # is properly assigned to ths instance class at the first "-="
            shot_enemy.endurance -= self.piercing
            if shot_enemy.endurance <= 0:
                shot_enemy.kill()
        if shot_enemy: self.kill()

        if self.position.distance(self.start_pos) > self.range_:
            self.kill()

class TeleShot(Shot):
    color = (255, 128, 0)
    range_ = 150
    movement_type = "tracking"

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


class GamePlay(object):

    def __init__(self):
        pygame.init()
        try:
            self.screen = pygame.display.set_mode(SIZE, FLAGS)
        except Exception:
            pygame.quit()
            raise


    def main(self):
        ticks = 0
        self.active_towertype = Tower
        self.map = Map()
        self.start_map()
        self.create_gui()
        try:
            while True:
                try:
                    self.iteration()
                except GameOver:
                    break
        except Exception as error:
            pygame.quit()
            if not isinstance(error, (GameOver, KeyboardInterrupt)):
                raise


    def user_iteration(self):
        pygame.event.pump()
        for event in pygame.event.get():
            if event.type == MOUSEBUTTONDOWN:
                if self.gui(event):
                    pass
                elif self.tower_clicked(event):
                    pass
                else:
                    self.map.towers.add(
                        self.active_towertype(self.map, Vector(event.pos)))
            elif event.type == KEYDOWN and event.key == K_ESCAPE:
                raise GameOver

    def iteration(self):
        object_types = "enemies towers shots objective"
        self.user_iteration()
        for group in (getattr(self.map, type_) for type_ in object_types.split()):
            group.clear(self.screen, draw_bg)
            group.update()
            group.draw(self.screen)
        self.draw_gui()
        pygame.display.flip()
        pygame.time.delay(FRAMERATE)

    def start_map(self):
        obj = Objective(self.map, Vector(randint(0, SIZE[0]), randint(0, SIZE[1])))
        self.map.objective.add(obj)
        for enemy_kind, number in zip((Enemy, StrongEnemy, FastEnemy), WAVE_ENEMIES ):
            for i in range(number):
                enemy = enemy_kind(self.map,
                            Vector(randint(0, SIZE[0]), randint(0, SIZE[1])))
                self.map.enemies.add(enemy)

    def create_gui(self):
        SLOTSIZE = 45
        SLOTCOLS = 2
        SLOTROWS = 5
        # This is in % of screen size:
        GUIPOS = (10, 50)
        self.towertypes = [Tower, TeleTower]
        self.gui_rect = pygame.Rect((0,0, SLOTCOLS * SLOTSIZE, SLOTROWS * SLOTSIZE))
        self.gui_rect.center = int(GUIPOS[0] * SIZE[0] / 100.0), int(GUIPOS[1] * SIZE[1] / 100.0)
        self.gui_rects = []
        self.gui_icons = Group()
        index = 0
        for y in xrange(SLOTROWS):
            for x in xrange(SLOTCOLS):
                slot_rect = pygame.Rect((self.gui_rect.left + x * SLOTSIZE,
                                        self.gui_rect.top + y * SLOTSIZE,
                                        SLOTSIZE, SLOTSIZE))
                self.gui_rects.append(slot_rect)
                if index < len(self.towertypes):
                    self.gui_icons.add(self.towertypes[index](self.map, slot_rect.center))
                index += 1

    def draw_gui(self):
        for rect in self.gui_rects:
            pygame.draw.rect(self.screen, (255,255,255),  rect, 1)
        self.gui_icons.draw(self.screen)


    def gui(self, event):
        if not self.gui_rect.collidepoint(event.pos):
            return False
        for rect, towertype in zip(self.gui_rects, self.towertypes):
            if rect.collidepoint(event.pos):
                self.active_towertype = towertype
                break
        return True

    def tower_clicked(self, event):
        for tower in self.map.towers:
            if tower.rect.collidepoint(event.pos):
                break
        else:
            return False
        original_image = tower.image
        tower.image = pygame.surface.Surface((tower.size, tower.size))
        tower.image.fill((255,255,255))
        tower.piercing = 300
        def restore_tower(instance):
            if hasattr(instance, "piercing"):
                delattr(instance, "piercing")
            instance.image = original_image
        tower.events.post(Event("after_shot", restore_tower))
        return True


if __name__ == "__main__":
    g = GamePlay()
    g.main()

