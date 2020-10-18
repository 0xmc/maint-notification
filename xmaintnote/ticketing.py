#!/bin/env python3

"""Handling events as tickets

The goal here is, provided a maintenance event, create an event if not a
duplicate. To determine if not duplicate, use some combination of values to
form a key. Methods to delete, update, and otherwise transform the ticket
should be available

A base class, Ticket, is provided to do some boiler plate things and enforce a
consistent interface.
"""

from textwrap import dedent

from jira import JIRA


class Ticket(object):
    """Base class for a ticket

    Purpose of this is to provide standard methods for retrieving duplicates,
    creating event, and deleting.

    Implementation details should be self-contained to each subclass but not
    really different from the interface perspective.

    Attributes:
        event (XMaintNoteEvent)
        acconut (str)
        impact (str)
        maintenance_id (str)
        object_id (str)
        provider (str)
        key (str): String that can try to be used to be unique among
                   maintenances
        title (str): Generated title that may be used as a ticket title
        body (str): Generated body thath may be used as a ticket description
        ticket: Optional to add by subclass, instance of ticket in the ticket
            system
    """

    def __init__(self, event, **kwargs):
        """Initializes and runs _post_init()

        Event is the only required input with any kwargs being accepted and
        forworded to ``self._post_init``. Purpose of the ``_post_init`` method
        is to facilitate each type of ticketing system to mutate the event data
        in however it needs without overloading ``__init__`` itself.

        A key is created using the provider, account, and maintenance-id keys
        of the event. How this is implemented by a ticketing system to take
        advantage of is up to the subclass.

        Args:
            event (XMaintNoteEvent): Maintenance Event
        """
        self.event = event
        self.account = event['X-MAINTNOTE-ACCOUNT']
        self.impact = event['X-MAINTNOTE-IMPACT']
        self.maintenance_id = event['X-MAINTNOTE-MAINTENANCE-ID']
        self.object_id = event['X-MAINTNOTE-OBJECT-ID']
        self.provider = event['X-MAINTNOTE-PROVIDER']
        self.ticket = None

        factors = [
            self.provider,
            self.account,
            self.maintenance_id,
        ]

        self.key = '{}:{}:{}'.format(*factors)

        self.title = '{provider} {impact} Maintenance for {account}'.format(
            provider=self.provider,
            impact=self.impact,
            account=self.account,
        )

        body = '''
        {provider} is having a maintenance of {impact}. Affected account number
        is {account}.

        Start time: {start_time}
        End time: {end_time}
        Impact: {impact}
        Account: {account}
        '''.format(
            provider=self.provider,
            impact=self.impact,
            account=self.account,
            start_time=str(event['DTSTART'].dt),
            end_time=str(event['DTEND'].dt),
        )
        self.body = dedent(body)

        self._post_init(**kwargs)

    def _post_init(self, **kwargs):
        pass

    def create(self):
        """Overload to create a ticket in the system"""
        raise NotImplemented('Subclass must overload this method')

    def close(self):
        """Overload to close a ticket in the system"""
        raise NotImplemented('Subclass must overload this method')

    def exists(self):
        """Overload to determine if this event exists in ticket form already"""
        raise NotImplemented('Subclass must overload this method')


class JiraTicket(Ticket):
    """Ticket driver for JIRA

    Supports adding list of watchers to maintenance issues created, custom
    finishing transition for when calling close, and custom issue types.

    Priorities will be mapped according to the impact status of the
    maintenance. A preferred mapping can be provided otherwise it defaults to
    using the Vanilla JIRA install names, eg:
        >>> {
                'NO-IMPACT': {'name': 'Low'},
                'REDUCED-REDUNDANCY': {'name': 'Medium'},
                'DEGRADED': {'name': 'High'},
                'OUTAGE': {'name': 'Highest'},
            }

    Example:
        >>> type(event)
        xmaintnote.event.XMaintNoteEvent
        >>> tkt = JiraTicket(
                event,
                url='http://localhost',
                username='admin',
                password='admin',
                watchers='noc',
            )
        >>> tkt.exists()
        False
        >>> tkt.create()
        True
        >>> tkt.exists()
        True
        >>> tkt.ticket
        <JIRA Issue: key=u'MAINT-14', id=u'10013'>
        >>> tkt.impact
        vText('NO-IMPACT')
        >>> tkt.ticket.fields.priority
        <JIRA Priority: name=u'Low', id=u'4'>
        >>> tkt.ticket.fields.labels
        [u'example.com:137.035999173:WorkOrder-31415']
    """

    def _post_init(
            self,
            url='http://localhost:8080',
            username=None,
            password=None,
            project='MAINT',
            issuetype='Task',
            finished_transition='Done',
            watchers=None,
            pri_mapping=None,
    ):
        """Setup to initialize Jira client and any required settings

        If username or password aren't provided, will attempt to do actions as
        anonymous

        Args:
            url (str): URL to jira server. MUST have the URL scheme (http://)
            username (str): Username (if applicable)
            password (str): Password (if applicable)
            project (str): JIRA project handle
            issuetype (str): Issue type to file these issues as
            watchers (list): List of usernames to add as watchers to the maints
            finished_transition (str): Transition to move the issue into when
                calling the ``.close`` method. Default: Done
            pri_mapping (str): Map of maintenance impact name to JIRA priority
                dict. eg, {'NO-IMPACT': {'name': 'Low'}}
        """

        # If either part of the credential tuple is unprovided, default to
        # anonymous
        credentials = (username, password)
        if not all(credentials):
            basic_auth = None
        else:
            basic_auth = credentials

        if not watchers:
            watchers = []
        if not pri_mapping:
            pri_mapping = {
                'NO-IMPACT': {'name': 'Low'},
                'REDUCED-REDUNDANCY': {'name': 'Medium'},
                'DEGRADED': {'name': 'High'},
                'OUTAGE': {'name': 'Highest'},
            }

        self.jira = JIRA(url, basic_auth=basic_auth)
        self.project = project
        self.issuetype = issuetype
        self.finished_transition = finished_transition
        self.watchers = watchers
        self.pri_mapping = pri_mapping

    def exists(self):
        """Return bool for whether maintenance issue exists for this event

        Improvements: Currently not handling the case where multiple issues are
        returned which may hint that the key used isn't unique enough or people
        have manually added the same label to other things. Also no exception
        handling mostly because the exception return by JIRA is pretty
        descriptive

        Returns:
            exists (bool)
        """
        existing = self.jira.search_issues('labels = {}'.format(self.key))
        if existing:
            self.ticket = existing[0]
        return True if existing else False

    def create(self):
        """Create issue for event

        Pre-check factors such as chehcking if this is a duplicate. If so, stop
        further actions.

        Returns:
            success (bool)
        """
        jira = self.jira

        # If issue doesn't exist, create it. Else return False for inability
        # Add watchers to the new ticket
        if not self.exists():
            options = {
                'project': self.project,
                'summary': self.title,
                'labels': [self.key],
                'description': self.body,
                'issuetype': {'name': self.issuetype},
                'priority': self.pri_mapping[self.impact],
            }
            new_issue = jira.create_issue(fields=options)

            self.ticket = new_issue
            [self._add_watcher(new_issue, w) for w in self.watchers]
            return True
        else:
            return False

    def close(self):
        """Return bool representing success or failure for closing issue

        If issue doesn't exist, will return False because it can't close.

        Returns:
            success (bool)
        """
        jira = self.jira
        finished_transition = self.finished_transition
        if self.exists():
            # Fetch the transitions that we can put the current issue into.
            # Search through these for the provided ``finished_transition``
            # from init. If not found, raise error.
            tkt = self.ticket
            transitions = jira.transitions(tkt)
            transition_ids = [
                t['id'] for t in transitions
                if t['name'] == self.finished_transition
            ]
            if not transition_ids:
                raise ValueError(
                    'Transition "{}" not found'.format(finished_transition)
                )

            t = transition_ids[0]
            jira.transition_issue(tkt, t)
        else:
            return False

    def _add_watcher(self, issue, watcher):
        """Add watcher to issue"""
        self.jira.add_watcher(issue, watcher)
