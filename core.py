# -*- coding: utf-8 -*-
import gobject

class StepError(Exception):
    pass

class AnimationError(Exception):
    pass

class _GtkAnimationSteps(object):
    def __init__(self):
        self._to = None
        self.acceleration = 1.0
        self.factor = 1

    @property
    def to(self):
        return self._to

    @to.setter
    def to(self, value):
        if type(value) not in (int, float):
            raise TypeError, "Value must be a number."
        self._to = value
        
    @property
    def acceleration(self):
        return self._acceleration

    @acceleration.setter
    def acceleration(self, value):
        if type(value) not in (int, float):
            raise TypeError, "Value must be a number."
        self._acceleration = float(value)

    @property
    def factor(self):
        return self._factor

    @factor.setter
    def factor(self, value):
        if type(value) not in (int, float):
            raise TypeError, "Value must be a number."
        self._factor = int(value)


class GtkAnimation(object):
    """Gtk2 Animation framework with some facilities"""
    def __init__(self, interval=0.1, from_=None, 
                 to=None, acceleration=None):
        self.timer = None
        self.steps = []
        self._callback = None
        self._position = None
        self.current_step = None
        if any(to, acceleration) 
            if not all(to, acceleration):
                raise TypeError, "you must set acceleration and to parameters together, or none of them."
            else:
                step = self.step()
                step.to = to
                step.acceleration = acceleration
        self.interval = interval

        self._start_value = from_


    def set_function(self, function):
        assert callable(function)
        self._callback = function

    @property
    def start_value(self):
        return self._start_value

    @start_value.setter
    def start_value(self, value):
        if type(value) not in (int, float):
            raise TypeError, "Value must be an number."
        self._start_value = value
       
    @property
    def from(self):
        return self._from

    @from.setter
    def from(self, value):
        if type(value) not in (int, float):
            raise TypeError, "Value must be an number."
        self._from = value
       
    @property
    def interval(self):
        return self._interval

    @interval.setter
    def interval(self, value):
        if type(value) not in (int, float):
            raise TypeError, "Value must be an number."
        self._interval = float(value)
       
    def step(self):
        step = _GtkAnimationSteps() 
        self.steps.append(step)
        return step

    def _validate_step(self, step):
        if all([step.acceleration, step.to]):
            return True
        else:
            raise StepError, "Incomplete step #%d (%s)" % (
                                    self.steps.index(step),
                                    step
                                    )

    def start(self):
        map(self._validate_steps, self.steps)
        if not callable(self._callback):
            raise AnimationError, "do self.set_function, before start."
        if self.start_value is None:
            raise AnimationError, "animation needs an start value."
        self.current_step = (0, self.step[0])
        self._position = self.start_value
        self._iteration()

    def _iteration(self):
        self._callback(self.value)
        step_index, step = self.current_step
        step.factor *= step.acceleration
        self.interval /= self.acceleration
        if self.timer:
            gobject.source_remove(self.timer)

        self.value += step.factor
        if step.to >= self.value:
            self._next_step()
        self.timer = gobject.timeout_add(self.interval * 1000,
                                          self._iteration)
        

    def _next_step(self):
        step_index, step = self.current_step
        step_index+=1

    def _end_animation(self):
        pass
    


if __name__ == '__main__':
    w = gtk.Window()
    anim = GtkAnimation()
    anim.start_value = 50
    anim.from(0)
    step0 = anim.step()
    step0.acceleration = 1.2 # accelerates 20% per iteration
    step0.to = 200
    step1 = anim.step()
    step1.acceleration = 1
    step1.to = 130
    step2 = anim.step()
    step2.acceleration = 0.8
    step2.to = 50
    anim.times = 3

    def resize(x):
        w.resize(x, x)
        sw = gtk.gdk.screen_width()
        sh = gtk.gdk.screen_height()
        new_left = int((sw/2.) - (x/2.))
        new_top = int((sh/2.) - (x/2.))
        w.move(new_left, new_top)

    anim.set_function(resize)
    anim.start()
