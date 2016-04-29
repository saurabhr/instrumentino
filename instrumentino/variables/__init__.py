'''
Variables
=========

A :class:`Variable` is a widget for showing and setting data on the screen.
The values of variables are serialized by turning them to a percentage.
Percentages are used for communication values between variables and channels.
Variable values are displayed on the screen by converting them into text.
Access to a variable's value in python is given by the :attr:`value`
attribute (variable.value). This returns the native value for this variable
(e.g. the chosen text in a spinner or the value within the variable's range
for an analog variable). The textual representation of a variable's value may
also be accessed by the :attr:`text` attribute (variable.text).

This is implemented in each of the sub-classes separately.
There are 3 principle types of variables:
- :class:`AnalogVariable`
    Handles analog data, represented by a :class:`TextInput`.
    Only this variable may have units.
- :class:`DigitalVariable`
    Handles digital data, represented by a :class:`Spinner`.
- custom structured variables
    Handle data that needs to be presented in a custom structured way.
    An example is :class:`TimeVariable` which represents the time in a
    :class:`TextInput` in the following way: 00:00:00.00
    (hours:minutes:seconds.miliseconds). The native serial value for this
    variable is the number of seconds.

'''

from __future__ import division
from kivy.properties import ObjectProperty, DictProperty, ListProperty, NumericProperty, StringProperty, OptionProperty, BooleanProperty, AliasProperty
import time
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.spinner import Spinner
from instrumentino.cfg import *
import re
from kivy.uix.textinput import TextInput
from kivy.app import App
from kivy.event import EventDispatcher

class Variable(BoxLayout):
    '''A variable widget for showing different types of variables on the screen.
    When given a channel_in argument, their value will be automatically updated by this channel.
    When given a channel_out argument, the value the user enters will be communicated out by that channel.
    
    Subclasses are responsible of screen presentation of the variable.
    '''

    name = StringProperty()
    '''The variable's name on the screen
    '''
    
    user_is_editing = BooleanProperty(False)
    '''Is the user currently editing the variable's value.
    This attribute should be updated by sub-classes.
    '''
    
    value = ObjectProperty()
    '''Return the native value for the variable. Default is text.
    Sub-classes should implement this for different behaviors. 
    '''

    channel_in = ObjectProperty(None)
    '''The input channel
    '''
    
    channel_out = ObjectProperty(None)
    '''The output channel
    '''

    def get_text_value(self):
        return self.value_to_text(self.value)
    text = AliasProperty(get_text_value)
    '''A property to access the variable's value as text.
    '''
    
    def text_to_value(self, text):
        '''Return the native value for this variable by translating a textual input.
        It is used to receive input from the user.
        Default is a simple cast to the variable's value's type.
        '''
        return type(self.value)(text)
    
    def value_to_text(self, value):
        '''Return the textual representation of the variable's value.
        It is used to display the variable's value on the screen.
        Default is a simple cast to text.
        '''
        return str(value)

    def percentage_to_value(self, percentage):
        '''Return the native value for this variable by translating a percentage.
        Sub-classes should implement this if they want to be able to receive
        data from input channels.
        '''
        raise NotImplementedError()
    
    def value_to_percentage(self, value):
        '''Translate the variable's value into a percentage.
        Sub-classes should implement this if they want to be able to transmit
        data to output channels.
        '''
        raise NotImplementedError()
        
    def __init__(self, **kwargs):
        super(Variable, self).__init__(**kwargs)
        
        self.name = self.name or create_default_name(self)
        
        # Let the channels keep a reference to us
        if self.channel_in:
            self.channel_in.variable = self
            
        if self.channel_out:
            self.channel_out.variable = self
            
    def user_entered_text(self, text):
        '''When the user sets the variable's value, act upon it and write it to the controller.
        '''
        self.value = self.text_to_value(text)
        
        if self.channel_out:
            self.channel_out.write(self.value_to_percentage(self.value))


    def new_data_arrived(self, percentage):
        '''Handle incoming data from the input channel (if it exists).
        '''
        
        self.value = self.percentage_to_value(percentage)
        
        # Don't update the text while the user is editing
        if not self.user_is_editing:
            self.value_display.text = self.text
        

class AnalogVariable(Variable):
    '''An analog variable
    '''

    upper_limit = NumericProperty()
    '''The upper limit this variable accepts
    '''
    
    lower_limit = NumericProperty()
    '''The lower limit this variable accepts
    '''
    
    units = StringProperty()
    '''The units of this variable
    '''

    def value_to_text(self, value):
        '''Return the textual representation of the variable's value.
        It is used to display the variable's value on the screen.
        '''
        return '{:2.2f}'.format(value)
    
    def __init__(self, **kwargs):
        check_for_necessary_attributes(self, ['range', 'units'], kwargs)
        super(AnalogVariable, self).__init__(**kwargs)
        
        # Let the user define the limits as a range.
        self.upper_limit = self.range[1]
        self.lower_limit = self.range[0]
            

class AnalogVariableUnipolar(AnalogVariable):
    '''An analog variable for unipolar values
    '''

    def percentage_to_value(self, percentage):
        '''Return the native value for this variable by translating a percentage.
        '''
        return self.lower_limit + percentage / 100 * (self.upper_limit - self.lower_limit)
    
    def value_to_percentage(self, value):
        '''Translate the variable's value into a percentage.
        '''
        return (value - self.lower_limit) / (self.upper_limit - self.lower_limit) * 100
        
    def __init__(self, **kwargs):
        super(AnalogVariableUnipolar, self).__init__(**kwargs)
        
        # Check the range
        if self.upper_limit * self.lower_limit < 0: raise ValueError('Range should be unipolar')

        
class AnalogVariablePercentage(AnalogVariableUnipolar):
    '''An analog variable for percentage values
    '''

    range = [0, 100]
    units = '%'
    '''Set necessary attributes.
    '''
    
    def __init__(self, **kwargs):
        super(AnalogVariablePercentage, self).__init__(**kwargs)
        
        
class AnalogVariableDurationInSeconds(Variable):
    '''A variable that represents a duration of time, measured in seconds. 
    '''
    
    pattern = re.compile('(..):(..):(.*)')
    '''The time is presented in the format: 00:00:00.000 (hours:minutes:seconds.milliseconds).
    '''
    
    def text_to_value(self, text):
        '''Return the native value for this variable by translating a textual input.
        It is used to receive input from the user.
        '''
        match = self.pattern.match(text)
        h = int(match.group(1))
        m = int(match.group(2))
        s = float(match.group(3))
        
        # return the number of seconds
        print str(h*60*60 + m*60 + s)
        return h*60*60 + m*60 + s
    
    def value_to_text(self, value):
        '''Return the textual representation of the variable's value.
        It is used to display the variable's value on the screen.
        '''
        m, s = divmod(value, 60)
        h, m = divmod(m, 60)
        return '{:02d}:{:02d}:{:06.3f}'.format(h, m, s)

    def __init__(self, **kwargs):
        if not 'value' in kwargs:
            kwargs['value'] = 0
        super(AnalogVariableDurationInSeconds, self).__init__(**kwargs)


class DigitalVariable(Variable):
    '''A digital variable
    '''

    options = ListProperty()
    '''The list of possible values, ordered from lowest to highest.
    '''
    
    def percentage_to_value(self, percentage):
        '''Return the native value for this variable by translating a percentage.
        '''
        index = int(percentage / 100 * (len(self.options) - 1))
        return self.options[index]
    
    def value_to_percentage(self, value):
        '''Translate the variable's value into a percentage.
        '''
        return self.options.index(value) / (len(self.options) - 1) * 100
        
    def __init__(self, **kwargs):
        check_for_necessary_attributes(self, ['options'], kwargs)
        super(DigitalVariable, self).__init__(**kwargs)
        

class DigitalVariableOnOff(DigitalVariable):
    '''An On/Off digital variable.
    '''
    
    options = ['off', 'on']
    '''Set necessary attributes.
    '''
    
    def __init__(self, **kwargs):
        
        super(DigitalVariableOnOff, self).__init__(**kwargs)


class FloatInput(TextInput):
    '''A TextInput widget that allows only floating points numbers to be enterd.
    '''

    pattern = re.compile('[^0-9]')
    
    def insert_text(self, substring, from_undo=False):
        '''Make sure text is inserted correctly into the allowed pattern
        '''
        pattern = self.pattern
        if '.' in self.text:
            s = re.sub(pattern, '', substring)
        else:
            s = '.'.join([re.sub(pattern, '', s) for s in substring.split('.', 1)])
        return super(FloatInput, self).insert_text(s, from_undo=from_undo)
    
    
class DurationInput(TextInput):
    '''A TextInput widget that allows to input a duration of time.
    The time is presented in the format: 00:00:00.000 (hours:minutes:seconds.milliseconds)
    '''

    pattern = re.compile('[^0-9]')
    '''A pattern to match everything but digits
    '''

    total_seconds_digits = 2+2+2+3
    '''The number of digits to display. 2+2+2+3 for hours+minutes+seconds+milliseconds.
    '''
    
    last_text = StringProperty()
    '''Remember the text before the current change
    '''
    
    def cursor_advancement_in_real_text(self, cursor, digits_added):
        '''Calculate the new position of the cursor after adding a number
        of digits, considering the text format.
        '''
        separators_positions = [2,5,8]
        for _ in range(digits_added):
            # skip over separators
            if cursor in separators_positions:
                cursor += 1
            
            # advance cursor
            cursor += 1
        
        if cursor in separators_positions:
            cursor += 1
                
        return min(cursor, len(self.text)-1)
    
    def insert_text(self, substring, from_undo=False):
        '''Make sure text is inserted correctly into the allowed pattern
        The text should always have the form: '00:00:00.000'
        '''

        # Check if the user accidentally deleted some of the text
        if len(self.text) != len(self.last_text):
            cc, cr = self.cursor
            self.text = self.last_text
            self.cursor = (cc, cr)
            return

        # Only accept digits 
        pattern = self.pattern
        stripped_substring = re.sub(pattern, '', substring)
        
        # Replace the digits in the stripped text and check it doesn't contain too many digits
        cc, cr = self.cursor
        cc = self.cursor_advancement_in_real_text(cc, 0)
        new_stripped_text = re.sub(pattern, '', self.text[:cc]) + stripped_substring + re.sub(pattern, '', self.text[cc:])[len(stripped_substring):]
        new_stripped_text = new_stripped_text[:self.total_seconds_digits]
        
        # Format the text again for display
        milliseconds = new_stripped_text[-3:]
        new_stripped_text = new_stripped_text[:-3]
            
        new_formatted_text = ':'.join(re.findall('..', new_stripped_text))
        if len(milliseconds):
            new_formatted_text += '.' + milliseconds
        
        self.text = new_formatted_text
        
        # Set the cursor in the right place
        cc = self.cursor_advancement_in_real_text(cc, len(stripped_substring))
        self.cursor = (cc, cr)
        
        self.last_text = self.text 
        
    def do_backspace(self, from_undo=False, mode='bkspc'):
        '''Disable backspace.
        '''
        pass
    
    def select_text(self, start, end):
        '''Disable selection.
        '''
        pass
    
    
class SpinnerWithOnChoiceEvent(Spinner):
    '''A spinner with an additional event, that fires when the user chose an option.
    This is necessary to differentiate between text changes done by the user and changes done programatically.
    '''
    
    def __init__(self, **kwargs):
        super(SpinnerWithOnChoiceEvent, self).__init__(**kwargs)

        # Register the event        
        self.register_event_type('on_choice')
        
    def _on_dropdown_select(self, instance, data, *largs):
        '''Override this method to create the event.
        '''
        # Fire the event.
        self.dispatch('on_choice', data)
        
        # Call the parent method
        super(SpinnerWithOnChoiceEvent, self)._on_dropdown_select(instance, data, *largs)
        
    def on_choice(self, *args):
        '''A default handler for the on_choice event
        '''
        pass