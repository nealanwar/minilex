from game.GameState import GameState

from parser.symbols.symbols import *
from parser.EventSequence import *
from legacy.build_syntax_tree import *

from utils.parse_json import *

from typing import List

class EventExec():
    """
    Execute event sequence
    """
    def __init__(self, seq: EventSequence, context, while_resolving, event_source, invoker, invokee) -> None:
        self.seq: List[EventLine] = seq.seq

        # context event is being executed in (i.e. combat, Expedition, action phase, etc.)
        self.context = context

        self.event_source = event_source

        self.invoker = invoker

        self.invokee = invokee

        # while resolving
        self.while_resolving = while_resolving

        self.last_test = None
        self.may_subject = None

        self.execute()
        pass

    def change_resources(self, subject, res):
        """
        Change resources of some subject
        """
        assert isinstance(res, SYM_QUANTITY)

        type = res.type
        num = res.num

        if isinstance(type, SYM_SKILL):
            print(f'adding %d %s to %s' % (num, type.skill, subject.name))
            setattr(subject, type.skill, getattr(subject, type.skill) + num)

    def match(e, op):
        """
        Match current item to sequence item
        """
        return e[0], op.name
    
    def consume_next_condition(self, s, i):
        return i, s[i + 2]
    
    def consume_until_end(self, event: EventSymbol, s: List[EventLine], i):
        """
        Consume and discard lines until end of current event, taking care to note nested events of the same class
        """
        N = 1
        i = i + 1
        while N > 0 and i < len(s):
            if s[i].name == event.name:
                if isinstance(s[i], EventLineEnd):
                    N -= 1
                elif not isinstance(s[i], ConditionStart) and not isinstance(s[i], ResultStart):
                    N += 1
            i += 1
        return i
    
    def execute(self):
        """
        Execute events in order
        """
        i = 0
        s = self.seq
        while i < len(s):
            e = s[i]
            # print('\tparsing', e)

            if isinstance(e.content, SYM_WHILE_RESOLVING):
                # check that while resolving cond holds
                i, cond = self.consume_next_condition(s, i)
                if not isinstance(cond.content, SYM_SPELL_EFFECTS):
                    # if not, proceed to end of clause
                    print('not eligible while resolving other than', SYM_SPELL_EFFECTS())

                    # TODO: Write proper skip to end of tag function, which
                    # skips until it finds N end tags, with N starting t 1 and increasing by 1
                    # for every "begin" tag with the same name as this tag it finds (i.e. closing any intermediate tags of the same type)
                    i = self.consume_until_end(e.content, s, i)
                else:
                    print('while resolving eligible')
            
            elif isinstance(e.content, SYM_MAY):
                # get user input (TODO: of course make this some pop-up eventually)
                self.took_may_choice = 'yes' # input('Will you make this choice?')
                
                # if no, end
                if self.took_may_choice == 'no':
                    print('refused choice')
                    i = self.consume_until_end(e.content, s, i)

                else:
                    print('accepted may choice', e.content.orig_text)
                    # if so, get subject
                    self.may_subject = e.content.subject

                    i, cond = self.consume_next_condition(s, i)

            elif isinstance(e.content, SYM_GAIN):

                # decide subject
                gainer = None
                if isinstance(e.content.subject, SYM_CURR_INVESTIGATOR):
                    gainer = self.invoker
                # TODO other options

                # gain resource
                res = e.content.resource
                self.change_resources(gainer, res)


            i += 1
            pass