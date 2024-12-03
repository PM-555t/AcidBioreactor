from __future__ import annotations
from abc import ABC, abstractmethod

#Note to self: get rid of "waitToFinish" function, this was only for testing out the model

# The Reactor class is the context. It should be initiated with a default state.
class Reactor:
    _state = None
    _majorTimerDone = True
    _minorTimerDone = True
    _pumpOrMsr = False #False = measuring, not pumping

    #initialize with an annotation = 'None'
    def __init__(self, state: State) -> None:
        self.setReactor(state)
        self.stateNumber = state.stateNumber

    #way to change the state
    def setReactor(self, state: State):
        self._state = state
        self._state.reactor = self

    #way to check the state
    def curState(self):
        print(f"Reactor is in {type(self._state).__name__}")
        return self._state
    
    #and ways to check the timers
    def curMajorTimer(self):
        return self._majorTimerDone
    def curMinorTimer(self):
        return self._minorTimerDone
    
    #and manage the sub-state
    def curPumpAction(self):
        return self._pumpOrMsr

    #state transition
    def nextState(self,which):
        self._state.nextState(which)


#This is the common state interface
class State(ABC):
    
    @property
    def stateNumber(self):
        return self._stateNumber

    @property
    def reactor(self) -> Reactor:
        return self._reactor
    
    @property
    def majorTimerDone(self):
        return self._majorTimerDone
    
    @property
    def minorTimerDone(self):
        return self._minorTimerDone
    
    @property
    def pumpOrMsr(self):
        return self._pumpOrMsr
    
    @pumpOrMsr.setter
    def pumpOrMsr(self, pumpOrMsr) -> None:
        self._pumpOrMsr = pumpOrMsr

    @majorTimerDone.setter
    def majorTimerDone(self, majorTimerDone) -> None:
        self._majorTimerDone = majorTimerDone

    @minorTimerDone.setter
    def minorTimerDone(self, minorTimerDone) -> None:
        self._minorTimerDone = minorTimerDone
    
    @stateNumber.setter
    def stateNumber(self, stateNumber) -> None:
        self._stateNumber = stateNumber
    
    @reactor.setter
    def reactor(self, reactor: Reactor) -> None:
        self._reactor = reactor

    @abstractmethod
    def nextState(self) -> None:
        pass

#These are the concrete states
class Acidification(State):

    _stateNumber = 40

    def nextState(self,which) -> None:
        if which == 50:
            print('Moving to "Watch CO2"')
            self.reactor.setReactor(watchCO2())
        elif which == 71:
            print("Moving to Dilute Part A")
            self.reactor.setReactor(diluteA())
        else:
            print(f'Cannot transition from {self._stateNumber} to {which}')

class watchCO2(State):

    _stateNumber = 50

    def nextState(self,which) -> None:
        if which == 60:
            print('Moving to "Incubate"')
            self.reactor.setReactor(Incubate())
        elif which == 71:
            print('Moving to "Dilute Part A"')
            self.reactor.setReactor(diluteA())
        else:
            print(f'Cannot transition from {self._stateNumber} to {which}')

class Incubate(State):

    _stateNumber = 60

    def nextState(self,which) -> None:
        if which == 40:
            print('Moving to "Acidification"')
            self.reactor.setReactor(Acidification())
        elif which == 71:
            print('Moving to "Dilute Part A"')
            self.reactor.setReactor(diluteA())
        else:
            print(f'Cannot transition from {self._stateNumber} to {which}')

class diluteA(State):

    _stateNumber = 71

    def nextState(self,which) -> None:
        if which == 72:
            print('Moving to "Dilute Part B"')
            self.reactor.setReactor(diluteB())
        elif which == 40:
            print('Moving to "Acidification"')
            self.reactor.setReactor(Acidification())
        elif which == 60:
            print('Moving to "Incubation"')
            self.reactor.setReactor(Incubate())
        else:
            print(f'Cannot transition from {self._stateNumber} to {which}')

class diluteB(State):

    _stateNumber = 72

    def nextState(self,which) -> None:
        if which == 60:
            print('Moving to "Incubate"')
            self.reactor.setReactor(Incubate())
        if which == 71:
            print('Moving to "Dilute Part A"')
            self.reactor.setReactor(diluteA())
        else:
            print(f'Cannot transition from {self._stateNumber} to {which}')


if __name__ == "__main__":
    #client code
    print("Bioreactor main called.")