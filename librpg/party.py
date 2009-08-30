"""
The :mod:`party` module provides functions to manage character groups
and pools of characters that can be picked to join a group.
"""

import pygame

from librpg.image import ObjectImage
from librpg.locals import *

def default_party_factory(reserve, capacity=None, chars=None, leader=None,
                          party_state=None):
    return Party(reserve, capacity, chars, leader, party_state)

class Party(object):

    """
    A Party is a group of Characters that move together in a map.
    """

    def __init__(self, reserve, capacity=None, chars=None, leader=None,
                 party_state=None):
        """
        Initialize a party with the given parameters.
        
        *reserve* should be the CharacterReserve that contains the party's
        characters.
        
        *capacity* should be an integer with the maximum number of
        Characters the party can hold.
        
        *chars*, should be a list of the names of the initial characters.
        *leader* should be the name of the initial leader. By default the
        party is empty.
        
        If *party_state* is passed, *capacity*, *chars* and *leader* should
        not be specified. In this case, the party setup is loaded from
        *party_state*.

        :attr:`capacity`
            Maximum number of characters in the Party.

        :attr:`reserve`
            CharacterReserve that contains the party's characters

        :attr:`chars`
            List of characters in the party currently

        :attr:`leader`
            Character whose image will be displayed in the map.

        :attr:`avatar`
            PartyAvatar that represents the party in the map.
        """
        assert (capacity is None and chars is None and leader is None) or \
               party_state is None, \
               'Either (chars and leader and capacity) or party_state has'\
               'to be None.'
        self.capacity = capacity
        self.reserve = reserve
        self.chars = []
        self.leader = None
        self.avatar = None

        self.initialize(party_state)
        reserve.register_party(self)
        
        if chars is not None:
            for char in chars:
                self.add_char(char)

        if leader is not None:
            self.leader = leader

    def add_char(self, name):
        """
        Insert a Character in the Party.

        *name* should be the character's name.

        Return True is the character was added, False if the operation
        failed, which happens either because the Character already was
        in the Party or because it is already full.
        """
        if (name not in self.reserve.get_names()
            or len(self.chars) >= self.capacity):
            return False
        else:
            self.reserve._allocate_char(name, self)
            self.chars.append(name)
            if self.leader is None:
                self.set_leader(name)
            return True

    def remove_char(self, name):
        """
        Remove a Character from the Party.

        *name* should be the character's name.

        Return True is the character was removed, False if the operation
        failed because the Character was not found in the party.
        """
        if name in self.chars:
            self.reserve._allocate_char(name, None)
            self.chars.remove(name)
            if self.leader == name:
                if len(self.chars) == 0:
                    self.set_leader(None)
                else:
                    self.set_leader(self.chars[0])
            return True
        else:
            return False

    def destroy(self):
        """
        Return a Party's characters to an available state.
        """
        self.reserve._destroy_party(self)

    def empty(self):
        """
        Return whether the party is empty.
        """
        return len(self.chars) == 0

    def __repr__(self):
        if len(self.chars) == 0:
            return '(Empty party)'
        else:
            chars = ', '.join([str(c) for c in self.chars if c != self.leader])
            return '(Leader: %s, %s)' % (self.leader, chars)

    def get_char(self, name):
        """
        Return the Character instance of the character with the given
        name.
        """
        if name not in self.chars:
            return None
        else:
            return self.reserve.get_char(name)

    def get_image(self, avatar):
        """
        Return the image to represent the Party on the map.
        
        *avatar* does not need to be specified, unless a class derived from
        Party wants to have an image that depends on it and overloads
        this function.
        """
        assert self.leader is not None, 'A Party with no characters may not be \
                                        displayed'
        return self.get_char(self.leader).image

    def save(self):
        return ((self.capacity, self.chars, self.leader),
                self.custom_save())

    def custom_save(self):
        """
        *Virtual.*
        
        Return a serializable local state to store the party's
        information.
        """
        return None

    def initialize(self, party_state=None):
        if party_state is None:
            return

        data = party_state[0]
        self.capacity = data[0]
        self.chars = data[1]
        self.set_leader(data[2])
        
        self.custom_initialize(party_state[1])

    def custom_initialize(self, party_state=None):
        """
        *Virtual.*
        
        Initialize whatever fields depend on the state that was saved in a
        previous game.

        *party_state* is the local state returned by save() when the state
        was saved.
        """
        pass

    def set_leader(self, new_leader):
        self.leader = new_leader
        if self.avatar is not None:
            self.avatar.reload_image()


class CharacterReserve(object):

    """
    A CharacterReserve is a container for characters that can be used
    in Parties.
    """

    def __init__(self, character_factory,
                 party_factory=default_party_factory):
        """
        *Constructor.*
        
        *character_factory* that, given a
        character name, returns an instance of that character.
        
        *party_factory* should be a factory function that returns an
        instance of Party or some derived class, given a capacity, a
        reserve and ((a list of character names and a leader name) or
        a party state). This defaults to the base Party constructor.

        :attr:`chars`
            Dict mapping character names to the Characters in the reserve.

        :attr:`party_allocation`
            Dict mapping character names in the reserve to the Party each
            of them is in.

        :attr:`parties`
            List of Parties created by this reserve.

        :attr:`character_factory`
            Factory function that, given a name and possibly a character
            state, returns an instance of the related character.

        :attr:`party_factory`
            Factory function that returns an instance of Party or some
            derived class, given a capacity, a reserve and ((a list of
            character names and a leader name) or a party state). This
            defaults to the base Party constructor.
        """
        self.chars = {}
        self.party_allocation = {}
        self.parties = []
        self.character_factory = character_factory
        self.party_factory = party_factory

    def add_char(self, name, char_state=None):
        """
        Add a Character to the reserve.
        
        *name* should be the character's name. If the character is
        supposed to be newly crated, *char_state* should be None.
        If it is being loaded, *char_state* should be a serializable
        with the necessary data.
        """
        self.chars[name] = self.character_factory(name, char_state)
        self.party_allocation[name] = None

    def remove_char(self, name):
        """
        Remove a character from the reserve.
        
        *name* should be the character's name.
        
        Return the Character if he was in the reserve, None otherwise.
        """
        if self.chars.has_key(name):
            char = self.chars[name]
            if self.party_allocation[name] is not None:
                self.party_allocation[name].remove_char(name)
            del self.chars[name]
            del self.party_allocation[name]
            return char
        else:
            return None

    def register_party(self, party):
        self.parties.append(party)
        for char in party.chars:
            self._allocate_char(char, party)

    def _destroy_party(self, party):
        assert party in self.parties, 'Trying to destroy a Party not in this \
                                       reserve'
        for char in party.chars:
            self._allocate_char(char, None)
        self.parties.remove(party)

    def _allocate_char(self, name, party):
        assert name in self.get_names(), 'Character is not in reserve'
        assert party is None or party in self.parties, 'Party is not in reserve'
        self.party_allocation[name] = party

    def get_default_party(self):
        if self.parties:
            return self.parties[0]
        else:
            return None

    def get_char(self, name):
        """
        Return the Character mapped to *name* in the reserve.

        None is returned if no character with that name was found.
        """
        return self.chars.get(name, None)

    def get_names(self):
        """
        Return a list of the character names in the reserve.
        """
        return self.chars.keys()

    def get_chars(self):
        """
        Return a list of the Characters in the reserve.
        """
        return self.chars.values()

    def __repr__(self):
        return self.party_allocation.__repr__()

    def save(self):
        # Save characters
        result = {}
        result[CHARACTERS_LOCAL_STATE] = {}
        for char in self.get_chars():
            result[CHARACTERS_LOCAL_STATE][char.name] = char.save()

        # Save parties
        result[PARTIES_LOCAL_STATE] = []
        for party in self.parties:
            result[PARTIES_LOCAL_STATE].append(party.save())
        return result
    
    def initialize(self, state=None):
        if state is None:
            return
        if state.has_key(CHARACTERS_LOCAL_STATE):
            for name, char_state in state[CHARACTERS_LOCAL_STATE].iteritems():
                self.add_char(name, char_state)
        if state.has_key(PARTIES_LOCAL_STATE):
            for party_state in state[PARTIES_LOCAL_STATE]:
                self.party_factory(self, party_state=party_state)


class Character(object):

    """
    A Character is a person that composes player controlled parties.
    
    Typically Characters will walk in maps organized in parties - 
    possibly a 1-Character party -, engage in battle and so on. They
    can be removed and added to parties. Typically parties have a
    limited number of Characters, such that only a couple can be picked
    from the CharacterReserve.
    """

    def __init__(self, name=None, image_file=None, index=0, char_state=None):
        """
        *Constructor.*
        
        Specify the *name* of the character, the name of the *image_file*
        where the character's sprites are, and the *index* by which the
        sprites can be found in the object image file.

        :attr:`name`
            A string with the character's *name* as it should be displayed.
            Must be unique.

        :attr:`image_file`
            Name of the file with the character's sprites.

        :attr:`image`
            ObjectImage with the character's sprites.
        """
        assert name is not None or char_state is not None, 'Cannot determine \
               the character\'s name'
        self.name = name
        self.image_file = image_file
        if image_file:
            self.image = ObjectImage(self.image_file, index)
        else:
            self.image = None
        self.initialize(char_state)

    def __repr__(self):
        return self.name

    def save(self):
        return (self.name, self.custom_save())

    def custom_save(self):
        """
        *Virtual.*
        
        Return a serializable local state to store the character's
        information.
        """
        return None

    def initialize(self, char_state=None):
        if char_state is None:
            return
        self.name = char_state[0]
        self.custom_initialize(char_state[1])

    def custom_initialize(self, char_state=None):
        """
        *Virtual.*
        
        Initialize whatever fields depend on the state that was saved in a
        previous game.

        *char_state* is the local state returned by custom_save() when the
        state was saved.
        """
        pass
