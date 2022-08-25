import pygame
import neat
import time
import os
import random

# NEAT:
'''
Inputs: Bird y coords, distance of top pipe and bird, distance of bottom pipe and bird
Outputs: Jump or not
Activation Function: TanH (outputs a value from -1 to 1), jump if the value is greater than 0.5
Population Size: 100 (how many birds will be running each generation)
Fitness Function: distance --> how far the bird travelled (function to evaluate how the birds performed each generation)
Max Generations: 30 (limit of turns to get satisfactory result, or reset algorithm)
'''

pygame.font.init()  # initialize the font

WIN_WIDTH = 500
WIN_HEIGHT = 800

GEN = 0

BIRD_IMGS = [pygame.transform.scale2x(pygame.image.load('imgs/bird1.png')),  # scale2x makes the image two times bigger
             pygame.transform.scale2x(pygame.image.load('imgs/bird2.png')),
             pygame.transform.scale2x(pygame.image.load('imgs/bird3.png'))]

PIPE_IMG = pygame.transform.scale2x(pygame.image.load('imgs/pipe.png'))
BASE_IMG = pygame.transform.scale2x(pygame.image.load('imgs/base.png'))
BG_IMG = pygame.transform.scale2x(pygame.image.load('imgs/bg.png'))

STAT_FONT = pygame.font.SysFont('comicsans', 50)


class Bird:
    IMGS = BIRD_IMGS
    MAX_ROTATION = 25  # how much the bird tilts when it 'flaps'
    ROT_VEL = 20  # velocity
    ANIMATION_TIME = 5

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.tilt = 0
        self.tick_count = 0  # used to calculate the physics of the bird
        self.vel = 0
        self.height = self.y
        self.img_count = 0  # current image of the bird for animation
        self.img = self.IMGS[0]

    def jump(self):
        self.vel = -10.5  # go up 10.5 pixels (-up/+down)
        self.tick_count = 0  # keep track of when the bird last jumped
        self.height = self.y  # keep track of the height the bird jumped from

    def move(self):
        self.tick_count += 1

        # measure displacement
        d = self.vel * self.tick_count + 1.5 * self.tick_count ** 2  # d = vt + (1/2)at^2
        # displacement: how many pixels the bird moves up or down in this frame

        if d >= 16:  # set terminal displacement
            d = 16

        if d < 0:  # set max jump displacement
            d -= 2

        self.y = self.y + d  # add the displacement to the y coords of the bird

        # tilt the bird
        # if the bird is moving upwards or the current bird position is higher than the previous one, tilt up
        if d < 0 or self.y < self.height + 50:
            # set tilt limit
            if self.tilt < self.MAX_ROTATION:
                self.tilt = self.MAX_ROTATION
        # else, tilt down
        else:
            # set the bird to gradually nosedive when moving down
            if self.tilt > -90:
                self.tilt -= self.ROT_VEL

    def draw(self, win):
        self.img_count += 1  # keep track of how many frames the current bird img is shown

        # loop through the images to create animation
        if self.img_count < self.ANIMATION_TIME:
            self.img = self.IMGS[0]
        elif self.img_count < self.ANIMATION_TIME * 2:
            self.img = self.IMGS[1]
        elif self.img_count < self.ANIMATION_TIME * 3:
            self.img = self.IMGS[2]
        elif self.img_count < self.ANIMATION_TIME * 4:
            self.img = self.IMGS[1]
        elif self.img_count == self.ANIMATION_TIME * 4 + 1:
            self.img = self.IMGS[0]
            self.img_count = 0

        # if the bird is nosediving freeze the wing movement
        if self.tilt <= -80:
            self.img = self.IMGS[1]
            self.img_count = self.ANIMATION_TIME * 2  # alter the timer so that the game does not skip a frame

        # tilt the bird around its center
        rotated_image = pygame.transform.rotate(self.img, self.tilt)
        new_rect = rotated_image.get_rect(center=self.img.get_rect(topleft=(self.x, self.y)).center)

        # blit the image
        win.blit(rotated_image, new_rect.topleft)

    def get_mask(self):  # used to get collisions
        # a mask is an array containing all the pixels in an box
        return pygame.mask.from_surface(self.img)


class Pipe:
    GAP = 200  # set the gap of the pipes that the bird passes through
    VEL = 5  # set velocity of pipe as the pipe moves and the bird does not

    def __init__(self, x):
        self.x = x
        self.height = 0

        self.top = 0  # keep track of where the top of the pipe is going to be drawn
        self.bottom = 0  # ... bottom ...
        self.PIPE_TOP = pygame.transform.flip(PIPE_IMG, False, True)  # flip the pipe img as the pipe top
        self.PIPE_BOTTOM = PIPE_IMG

        self.passed = False  # if the pipe has passed through the pipe
        self.set_height()  # randomly generate where the top and bottom positions of the pipe

    def set_height(self):
        self.height = random.randrange(50, 450)
        self.top = self.height - self.PIPE_TOP.get_height()  # get the coords of the top left of the pipe to draw it
        self.bottom = self.height + self.GAP

    def move(self):
        # change the x coords of the pipes based on the velocity of the pipes
        self.x -= self.VEL  # move the pipe towards the left of the screen

    def draw(self, win):
        win.blit(self.PIPE_TOP, (self.x, self.top))
        win.blit(self.PIPE_BOTTOM, (self.x, self.bottom))

    def collide(self, bird):
        bird_mask = bird.get_mask()
        top_mask = pygame.mask.from_surface(self.PIPE_TOP)
        bottom_mask = pygame.mask.from_surface(self.PIPE_BOTTOM)

        # calculate offset (how far away these masks are from each other)
        top_offset = (self.x - bird.x, self.top - round(bird.y))  # round up the y coords that may have decimal numbers
        bottom_offset = (self.x - bird.x, self.bottom - round(bird.y))

        # find the point of collision of the bird and pipe (returns None if there is no collision)
        b_point = bird_mask.overlap(bottom_mask, bottom_offset)
        t_point = bird_mask.overlap(top_mask, top_offset)

        if t_point or b_point:
            return True

        return False


class Base:
    VEL = 5
    WIDTH = BASE_IMG.get_width()
    IMG = BASE_IMG

    def __init__(self, y):
        self.y = y
        self.x1 = 0  # first base
        self.x2 = self.WIDTH  # continuing base

    def move(self):
        self.x1 -= self.VEL
        self.x2 -= self.VEL

        if self.x1 + self.WIDTH < 0:  # redraw the first base when it has left the screen
            self.x1 = self.x2 + self.WIDTH

        if self.x2 + self.WIDTH < 0:  # redraw the continuing base ...
            self.x2 = self.x1 + self.WIDTH

    def draw(self, win):
        win.blit(self.IMG, (self.x1, self.y))
        win.blit(self.IMG, (self.x2, self.y))


def draw_window(win, birds, pipes, base, score, gen):
    win.blit(BG_IMG, (0, 0))  # draw the background from the top left corner
    for pipe in pipes:
        pipe.draw(win)
    base.draw(win)
    for bird in birds:
        bird.draw(win)

    # draw the score
    text = STAT_FONT.render("Score: " + str(score), True, (255, 255, 255))
    win.blit(text, (WIN_WIDTH - 10 - text.get_width(), 10))

    # draw the generation
    text = STAT_FONT.render("Gen: " + str(gen), True, (255, 255, 255))
    win.blit(text, (10, 10))

    pygame.display.update()


def main(genomes, config):
    global GEN
    GEN += 1  # increment gen everytime main is ran
    nets = []  # list to keep track of the neural network that controls each bird
    ge = []  # list to keep track of the genomes

    birds = []  # list to save all the birds in a generation

    for _, g in genomes:  # genomes are tuples, we only need the second value which is g
        net = neat.nn.FeedForwardNetwork.create(g, config)
        nets.append(net)
        birds.append(Bird(230, 350))
        g.fitness = 0  # set the initial fitness of each genome to 0
        ge.append(g)

    base = Base(730)
    pipes = [Pipe(600)]

    win = pygame.display.set_mode((WIN_WIDTH, WIN_HEIGHT))
    clock = pygame.time.Clock()

    score = 0

    run = True
    while run:
        clock.tick(30)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
                pygame.quit()
                quit()

        # move the bird based on the neural network
        pipe_ind = 0
        if len(birds) > 0:
            # if the bird has passed a pipe, change the pipe the neural network targets to the second pipe in the list
            if len(pipes) > 1 and birds[0].x > pipes[0].x + pipes[0].PIPE_TOP.get_width():
                pipe_ind = 1
        # if there are no birds left, quit the game
        else:
            run = False
            break

        for x, bird in enumerate(birds):
            bird.move()
            ge[x].fitness += 0.1  # increase the fitness score by a little if the bird is still alive and moving

            # pass the input values into the neural network (height of bird, distance of top pipe and bird, distance of bottom pipe and bird)
            output = nets[x].activate((bird.y, abs(bird.y - pipes[pipe_ind].height), abs(bird.y - pipes[pipe_ind].bottom)))

            # output is a list, as we only have one output neuron, grab the first value
            if output[0] > 0.5:
                bird.jump()

        add_pipe = False
        rem = []  # list of pipes to remove
        for pipe in pipes:
            for x, bird in enumerate(birds):
                # check for collision
                if pipe.collide(bird):
                    ge[x].fitness -= 1  # deduct one from fitness score if bird hits a pipe
                    # remove the bird from all lists
                    birds.pop(x)
                    nets.pop(x)
                    ge.pop(x)

                if not pipe.passed and pipe.x < bird.x:  # if the bird passed the pipe, generate a new pipe
                    pipe.passed = True
                    add_pipe = True

            if pipe.x + pipe.PIPE_TOP.get_width() < 0:  # if the pipe is off the screen
                rem.append(pipe)

            pipe.move()

        if add_pipe:
            score += 1
            # increase fitness score if bird passes through a pipe
            for g in ge:
                g.fitness += 5

            pipes.append(Pipe(600))


        for r in rem:  # remove the pipes that are off the screen
            pipes.remove(r)

        for x, bird in enumerate(birds):
            if bird.y + bird.img.get_height() >= 730 or bird.y < 0:  # check if the bird hit the floor or ceiling
                # remove the bird from all lists
                birds.pop(x)
                nets.pop(x)
                ge.pop(x)

        base.move()
        draw_window(win, birds, pipes, base, score, GEN)


# load the config file
def run(path):
    # define the headers of the config file
    config = neat.config.Config(neat.DefaultGenome, neat.DefaultReproduction, neat.DefaultSpeciesSet,
                                neat.DefaultStagnation, path)

    p = neat.Population(config)  # generate population

    # format output
    p.add_reporter(neat.StdOutReporter(True))
    stats = neat.StatisticsReporter()
    p.add_reporter(stats)

    # run fitness function n times(generations)
    winner = p.run(main, 50)


if __name__ == '__main__':
    local_dir = os.path.dirname(__file__)
    config_path = os.path.join(local_dir, 'config-feedforward.txt')
    run(config_path)
