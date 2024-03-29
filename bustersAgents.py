from __future__ import print_function

from wekaI import Weka

# bustersAgents.py
# ----------------
# Licensing Information:  You are free to use or extend these projects for
# educational purposes provided that (1) you do not distribute or publish
# solutions, (2) you retain this notice, and (3) you provide clear
# attribution to UC Berkeley.
# 
# Attribution Information: The Pacman AI projects were developed at UC Berkeley.
# The core projects and autograders were primarily created by John DeNero
# (denero@cs.berkeley.edu) and Dan Klein (klein@cs.berkeley.edu).
# Student side autograding was added by Brad Miller, Nick Hay, and
# Pieter Abbeel (pabbeel@cs.berkeley.edu).
import math
from builtins import range
from builtins import object
import util
from game import Agent
from game import Directions
from keyboardAgents import KeyboardAgent
import inference
import busters

class NullGraphics(object):
    "Placeholder for graphics"
    def initialize(self, state, isBlue = False):
        pass
    def update(self, state):
        pass
    def pause(self):
        pass
    def draw(self, state):
        pass
    def updateDistributions(self, dist):
        pass
    def finish(self):
        pass

class KeyboardInference(inference.InferenceModule):
    """
    Basic inference module for use with the keyboard.
    """
    def initializeUniformly(self, gameState):
        "Begin with a uniform distribution over ghost positions."
        self.beliefs = util.Counter()
        for p in self.legalPositions: self.beliefs[p] = 1.0
        self.beliefs.normalize()

    def observe(self, observation, gameState):
        noisyDistance = observation
        emissionModel = busters.getObservationDistribution(noisyDistance)
        pacmanPosition = gameState.getPacmanPosition()
        allPossible = util.Counter()
        for p in self.legalPositions:
            trueDistance = util.manhattanDistance(p, pacmanPosition)
            if emissionModel[trueDistance] > 0:
                allPossible[p] = 1.0
        allPossible.normalize()
        self.beliefs = allPossible

    def elapseTime(self, gameState):
        pass

    def getBeliefDistribution(self):
        return self.beliefs


class BustersAgent(object):
    "An agent that tracks and displays its beliefs about ghost positions."

    def __init__( self, index = 0, inference = "ExactInference", ghostAgents = None, observeEnable = True, elapseTimeEnable = True):
        inferenceType = util.lookup(inference, globals())
        self.inferenceModules = [inferenceType(a) for a in ghostAgents]
        self.observeEnable = observeEnable
        self.elapseTimeEnable = elapseTimeEnable
        self.weka = Weka()
        self.weka.start_jvm()

    def registerInitialState(self, gameState):
        "Initializes beliefs and inference modules"
        import __main__
        self.display = __main__._display
        for inference in self.inferenceModules:
            inference.initialize(gameState)
        self.ghostBeliefs = [inf.getBeliefDistribution() for inf in self.inferenceModules]
        self.firstMove = True

    def observationFunction(self, gameState):
        "Removes the ghost states from the gameState"
        agents = gameState.data.agentStates
        gameState.data.agentStates = [agents[0]] + [None for i in range(1, len(agents))]
        return gameState

    def getAction(self, gameState):
        "Updates beliefs, then chooses an action based on updated beliefs."
        #for index, inf in enumerate(self.inferenceModules):
        #    if not self.firstMove and self.elapseTimeEnable:
        #        inf.elapseTime(gameState)
        #    self.firstMove = False
        #    if self.observeEnable:
        #        inf.observeState(gameState)
        #    self.ghostBeliefs[index] = inf.getBeliefDistribution()
        #self.display.updateDistributions(self.ghostBeliefs)
        return self.chooseActionWeka(gameState)

    def chooseAction(self, gameState):
        "By default, a BustersAgent just stops.  This should be overridden."
        return Directions.STOP

class BustersKeyboardAgent(BustersAgent, KeyboardAgent):
    "An agent controlled by the keyboard that displays beliefs about ghost positions."

    def __init__(self, index = 0, inference = "KeyboardInference", ghostAgents = None):
        KeyboardAgent.__init__(self, index)
        BustersAgent.__init__(self, index, inference, ghostAgents)

    def getAction(self, gameState):
        return BustersAgent.getAction(self, gameState)

    def chooseAction(self, gameState):
        return KeyboardAgent.getAction(self, gameState)

from distanceCalculator import Distancer
from game import Actions
from game import Directions
import random, sys

'''Random PacMan Agent'''
class RandomPAgent(BustersAgent):

    def registerInitialState(self, gameState):
        BustersAgent.registerInitialState(self, gameState)
        self.distancer = Distancer(gameState.data.layout, False)
        
    ''' Example of counting something'''
    def countFood(self, gameState):
        food = 0
        for width in gameState.data.food:
            for height in width:
                if(height == True):
                    food = food + 1
        return food
    
    ''' Print the layout'''  
    def printGrid(self, gameState):
        table = ""
        ##print(gameState.data.layout) ## Print by terminal
        for x in range(gameState.data.layout.width):
            for y in range(gameState.data.layout.height):
                food, walls = gameState.data.food, gameState.data.layout.walls
                table = table + gameState.data._foodWallStr(food[x][y], walls[x][y]) + ","
        table = table[:-1]
        return table
        
    def chooseAction(self, gameState):
        move = Directions.STOP
        legal = gameState.getLegalActions(0) ##Legal position from the pacman
        move_random = random.randint(0, 3)
        if   ( move_random == 0 ) and Directions.WEST in legal:  move = Directions.WEST
        if   ( move_random == 1 ) and Directions.EAST in legal: move = Directions.EAST
        if   ( move_random == 2 ) and Directions.NORTH in legal:   move = Directions.NORTH
        if   ( move_random == 3 ) and Directions.SOUTH in legal: move = Directions.SOUTH
        return move
        
class GreedyBustersAgent(BustersAgent):
    "An agent that charges the closest ghost."

    def registerInitialState(self, gameState):
        "Pre-computes the distance between every two points."
        BustersAgent.registerInitialState(self, gameState)
        self.distancer = Distancer(gameState.data.layout, False)

    def chooseAction(self, gameState):
        """
        First computes the most likely position of each ghost that has
        not yet been captured, then chooses an action that brings
        Pacman closer to the closest ghost (according to mazeDistance!).

        To find the mazeDistance between any two positions, use:
          self.distancer.getDistance(pos1, pos2)

        To find the successor position of a position after an action:
          successorPosition = Actions.getSuccessor(position, action)

        livingGhostPositionDistributions, defined below, is a list of
        util.Counter objects equal to the position belief
        distributions for each of the ghosts that are still alive.  It
        is defined based on (these are implementation details about
        which you need not be concerned):

          1) gameState.getLivingGhosts(), a list of booleans, one for each
             agent, indicating whether or not the agent is alive.  Note
             that pacman is always agent 0, so the ghosts are agents 1,
             onwards (just as before).

          2) self.ghostBeliefs, the list of belief distributions for each
             of the ghosts (including ghosts that are not alive).  The
             indices into this list should be 1 less than indices into the
             gameState.getLivingGhosts() list.
        """
        pacmanPosition = gameState.getPacmanPosition()
        legal = [a for a in gameState.getLegalPacmanActions()]
        livingGhosts = gameState.getLivingGhosts()
        livingGhostPositionDistributions = \
            [beliefs for i, beliefs in enumerate(self.ghostBeliefs)
             if livingGhosts[i+1]]
        return Directions.EAST


def get_next_score(gameState):
    x = gameState.getPacmanPosition()[0]
    y = gameState.getPacmanPosition()[1]
    next_score = gameState.getScore() - 1
    if gameState.data.agentStates[0].getDirection() == "North":
        y = + 1
    elif gameState.data.agentStates[0].getDirection() == "South":
        y = - 1
    elif gameState.data.agentStates[0].getDirection() == "West":
        x = - 1
    elif gameState.data.agentStates[0].getDirection() == "East":
        x = + 1
    if gameState.data.food[x][y]:
        next_score = next_score + 100
    elif gameState.getGhostPositions()[0] == (x,y) or gameState.getGhostPositions()[1] == (x,y) or \
            gameState.getGhostPositions()[2] == (x,y) or gameState.getGhostPositions()[3] == (x,y):
        next_score = next_score + 200
    return int(next_score)




class BasicAgentAA(BustersAgent):

    def registerInitialState(self, gameState):
        BustersAgent.registerInitialState(self, gameState)
        self.distancer = Distancer(gameState.data.layout, False)
        self.countActions = 0
        self.weka = Weka()
        self.weka.start_jvm()

    ''' Example of counting something'''
    def countFood(self, gameState):
        food = 0
        for width in gameState.data.food:
            for height in width:
                if(height == True):
                    food = food + 1
        return food

    ''' Print the layout'''
    def printGrid(self, gameState):
        table = ""
        #print(gameState.data.layout) ## Print by terminal
        for x in range(gameState.data.layout.width):
            for y in range(gameState.data.layout.height):
                food, walls = gameState.data.food, gameState.data.layout.walls
                table = table + gameState.data._foodWallStr(food[x][y], walls[x][y]) + ","
        table = table[:-1]
        return table

    def printInfo(self, gameState):
        print("---------------- TICK ", self.countActions, " --------------------------")
        # Map size
        width, height = gameState.data.layout.width, gameState.data.layout.height
        print("Width: ", width, " Height: ", height)
        # Pacman position
        print("Pacman position: ", gameState.getPacmanPosition())
        # Legal actions for Pacman in current position
        print("Legal actions: ", gameState.getLegalPacmanActions())
        # Pacman direction
        print("Pacman direction: ", gameState.data.agentStates[0].getDirection())
        # Number of ghosts
        print("Number of ghosts: ", gameState.getNumAgents() - 1)
        # Alive ghosts (index 0 corresponds to Pacman and is always false)
        print("Living ghosts: ", gameState.getLivingGhosts())
        # Ghosts positions
        print("Ghosts positions: ", gameState.getGhostPositions())
        # Ghosts directions
        print("Ghosts directions: ", [gameState.getGhostDirections().get(i) for i in range(0, gameState.getNumAgents() - 1)])
        # Manhattan distance to ghosts
        print("Ghosts distances: ", gameState.data.ghostDistances)
        # Pending pac dots
        print("Pac dots: ", gameState.getNumFood())
        # Manhattan distance to the closest pac dot
        print("Distance nearest pac dots: ", gameState.getDistanceNearestFood())
        # Map walls
        print("Map:")
        print( gameState.getWalls())
        # Score
        print("Score: ", gameState.getScore())


    def chooseAction(self, gameState):
        self.countActions = self.countActions + 1
        self.printInfo(gameState)
        move = random.choice(gameState.getLegalActions())
        legal = gameState.getLegalActions(0) ##Legal position from the pacman

        aux = 1000
        # search the nearest ghost
        for i in gameState.data.ghostDistances:
            if i != None and i < aux:
                aux = i
        # set the nearest ghost
        fantasma = gameState.data.ghostDistances.index(aux)

        resta = ((gameState.getPacmanPosition()[0] - gameState.getGhostPositions()[fantasma][0]), (gameState.getPacmanPosition()[1] - gameState.getGhostPositions()[fantasma][1]))
        if(resta[0] < 0) and Directions.EAST in legal: move = Directions.EAST
        if(resta[0] > 0) and Directions.WEST in legal:  move = Directions.WEST
        if(resta[1] < 0) and Directions.NORTH in legal:   move = Directions.NORTH
        if(resta[1] > 0) and Directions.SOUTH in legal: move = Directions.SOUTH

        #if   ( move_random == 0 ) and Directions.WEST in legal:  move = Directions.WEST
        #if   ( move_random == 1 ) and Directions.EAST in legal: move = Directions.EAST
        #if   ( move_random == 2 ) and Directions.NORTH in legal:   move = Directions.NORTH
        #if   ( move_random == 3 ) and Directions.SOUTH in legal: move = Directions.SOUTH

        return move

    def chooseActionWeka(self, gameState):
        x = []
        #posicion del pacman en el eje x
        #x.append(gameState.getPacmanPosition()[0])
        #posicion del pacman en el eje y
        #x.append(gameState.getPacmanPosition()[1])
        #numero de fantasmas vivos
        #x.append(gameState.getLivingGhosts().count(True))
        #fastama[i] vivo o muerto
        #for i in range(1, len(gameState.getLivingGhosts())):
            #x.append(str(gameState.getLivingGhosts()[i]))
        #direccion en la que se encuentra el fantasma más cercano
        x.append(str(BasicAgentAA.mostProbablyDirectionForWeka(self, gameState, 'NORTH')))
        x.append(str(BasicAgentAA.mostProbablyDirectionForWeka(self, gameState, 'SOUTH')))
        x.append(str(BasicAgentAA.mostProbablyDirectionForWeka(self, gameState, 'WEST')))
        x.append(str(BasicAgentAA.mostProbablyDirectionForWeka(self, gameState, 'EAST')))
        #angulo al fantasma más cercano
        x.append(BasicAgentAA.angleClosestGhost(self, gameState))
        #indicador de pared en las distintas direcciones
        x.append(str(gameState.hasWall(gameState.getPacmanPosition()[0] - 1, gameState.getPacmanPosition()[1])))
        x.append(str(gameState.hasWall(gameState.getPacmanPosition()[0], gameState.getPacmanPosition()[1] - 1)))
        x.append(str(gameState.hasWall(gameState.getPacmanPosition()[0] + 1, gameState.getPacmanPosition()[1])))
        x.append(str(gameState.hasWall(gameState.getPacmanPosition()[0], gameState.getPacmanPosition()[1] + 1)))
        #puntuacion actual
        #x.append(gameState.getScore())

        return self.weka.predict('./J48-bueno.model', x, './ficheros/pruebas/datos.arff')


    #todo almacena la informacion del tic anterior
    todo = ""
    def printLineData(self, gameState, move):
        #guardamos en una variable local la información del tick anterior
        buffer = BasicAgentAA.todo
        #controlamos el primer tick para no escribir la primera linea de manera defectuosa
        ignore_first = False
        if BasicAgentAA.todo == "":
            ignore_first = True
        #actualizamos el valor de la variable todo con la información actual para poder usarla en el tick siguiente
        BasicAgentAA.todo = str(gameState.getPacmanPosition()[0]) + "," + str(gameState.getPacmanPosition()[1]) + ","
        #BasicAgentAA.todo = BasicAgentAA.todo + str(gameState.data.agentStates[0].getDirection()) + ","
        #concatenamos la informacion de los fantasmas a la variable todo
        living_ghost = gameState.getLivingGhosts().count(True)
        BasicAgentAA.todo = BasicAgentAA.todo + str(living_ghost) + ","
        for i in range(1, len(gameState.getLivingGhosts())):
            BasicAgentAA.todo = BasicAgentAA.todo + str(gameState.getLivingGhosts()[i]) + ","
        for ghost in gameState.getGhostPositions():
            BasicAgentAA.todo = BasicAgentAA.todo + str(ghost[0]) + "," + str(ghost[1]) + ","
        for ghost in gameState.data.ghostDistances:
            BasicAgentAA.todo = BasicAgentAA.todo + (str(-1) if ghost is None else str(ghost)) + ","

        BasicAgentAA.todo = BasicAgentAA.todo + str(BasicAgentAA.mostProbablyDirection(self, gameState))
        BasicAgentAA.todo = BasicAgentAA.todo + str(BasicAgentAA.angleClosestGhost(self, gameState)) + ","
        BasicAgentAA.todo = BasicAgentAA.todo + str(gameState.hasWall(gameState.getPacmanPosition()[0] - 1, gameState.getPacmanPosition()[1])) + ","
        BasicAgentAA.todo = BasicAgentAA.todo + str(gameState.hasWall(gameState.getPacmanPosition()[0], gameState.getPacmanPosition()[1] - 1)) + ","
        BasicAgentAA.todo = BasicAgentAA.todo + str(gameState.hasWall(gameState.getPacmanPosition()[0] + 1, gameState.getPacmanPosition()[1])) + ","
        BasicAgentAA.todo = BasicAgentAA.todo + str(gameState.hasWall(gameState.getPacmanPosition()[0], gameState.getPacmanPosition()[1] + 1)) + ","
        BasicAgentAA.todo = BasicAgentAA.todo + str(-1 if gameState.getDistanceNearestFood() is None else gameState.getDistanceNearestFood()) + "," + str(gameState.getScore()) + "," + str(gameState.getNumFood()) + "," + str(move)
        if ignore_first:
            return ""
        return buffer + "," + str(gameState.getScore()) + "," + str(gameState.getLivingGhosts().count(True)) + "," + str(gameState.getNumFood()) + "\n"

    def angleClosestGhost(self, gameState):
        index = 0
        aux = 0
        minDistance = 100
        for ghost in gameState.data.ghostDistances:
            if ghost is not None:
                if ghost > 0 and ghost < minDistance:
                    minDistance = ghost
                    index = aux
            aux += 1
        myradians = math.atan2(gameState.getGhostPositions()[index][1] - gameState.getPacmanPosition()[1], gameState.getGhostPositions()[index][0] - gameState.getPacmanPosition()[0])
        if myradians < 0:
            myradians += 2 * math.pi

        angle = round(math.degrees(myradians)) % 360
        return angle

    def mostProbablyDirection(self, gameState):
        index = 0
        aux = 0
        minDistance = 100
        for ghost in gameState.data.ghostDistances:
            if ghost is not None:
                if ghost > 0 and ghost < minDistance:
                    minDistance = ghost
                    index = aux
            aux += 1

        up = False
        down = False
        left = False
        right = False
        if gameState.getPacmanPosition()[0] - gameState.getGhostPositions()[index][0] > 0:
            left = True
        if gameState.getPacmanPosition()[0] - gameState.getGhostPositions()[index][0] < 0:
            right = True
        if gameState.getPacmanPosition()[1] - gameState.getGhostPositions()[index][1] > 0:
            down = True
        if gameState.getPacmanPosition()[1] - gameState.getGhostPositions()[index][1] < 0:
            up = True
        return str(up) + "," + str(down) + "," + str(left) + "," + str(right) + ","

    def mostProbablyDirectionForWeka(self, gameState, direction):
        index = 0
        aux = 0
        minDistance = 100
        for ghost in gameState.data.ghostDistances:
            if ghost is not None:
                if ghost > 0 and ghost < minDistance:
                    minDistance = ghost
                    index = aux
            aux += 1

        up = False
        down = False
        left = False
        right = False
        if gameState.getPacmanPosition()[0] - gameState.getGhostPositions()[index][0] > 0:
            left = True
        if gameState.getPacmanPosition()[0] - gameState.getGhostPositions()[index][0] < 0:
            right = True
        if gameState.getPacmanPosition()[1] - gameState.getGhostPositions()[index][1] > 0:
            down = True
        if gameState.getPacmanPosition()[1] - gameState.getGhostPositions()[index][1] < 0:
            up = True

        if direction == 'NORTH':
            return str(up)
        elif direction == 'SOUTH':
            return str(down)
        elif direction == 'WEST':
            return str(left)
        elif direction == 'EAST':
            return str(right)