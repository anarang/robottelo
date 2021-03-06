# -*- encoding: utf-8 -*-
"""Test class for Architecture CLI"""

from robottelo.cli.architecture import Architecture
from robottelo.cli.base import CLIReturnCodeError
from robottelo.cli.factory import make_architecture
from robottelo.datafactory import (
    invalid_id_list,
    invalid_values_list,
    valid_data_list,
)
from robottelo.decorators import run_only_on, tier1
from robottelo.test import CLITestCase


class ArchitectureTestCase(CLITestCase):
    """Architecture CLI related tests."""

    @tier1
    def test_positive_create_with_name(self):
        """Successfully creates an Architecture.

        @Feature: Architecture

        @Assert: Architecture is created.
        """
        for name in valid_data_list():
            with self.subTest(name):
                architecture = make_architecture({'name': name})
                self.assertEqual(architecture['name'], name)

    @tier1
    def test_negative_create_with_name(self):
        """Don't create an Architecture with invalid data.

        @Feature: Architecture

        @Assert: Architecture is not created.
        """
        for name in invalid_values_list():
            with self.subTest(name):
                with self.assertRaises(CLIReturnCodeError):
                    Architecture.create({'name': name})

    @tier1
    def test_positive_update_name(self):
        """Successfully update an Architecture.

        @Feature: Architecture

        @Assert: Architecture is updated.
        """
        architecture = make_architecture()
        for new_name in valid_data_list():
            with self.subTest(new_name):
                Architecture.update({
                    'id': architecture['id'],
                    'new-name': new_name,
                })
                architecture = Architecture.info({'id': architecture['id']})
                self.assertEqual(architecture['name'], new_name)

    @tier1
    @run_only_on('sat')
    def test_negative_update_name(self):
        """Create Architecture then fail to update its name

        @feature: Architecture

        @assert: Architecture name is not updated
        """
        architecture = make_architecture()
        for new_name in invalid_values_list():
            with self.subTest(new_name):
                with self.assertRaises(CLIReturnCodeError):
                    Architecture.update({
                        'id': architecture['id'],
                        'new-name': new_name,
                    })
                result = Architecture.info({'id': architecture['id']})
                self.assertEqual(architecture['name'], result['name'])

    @tier1
    @run_only_on('sat')
    def test_positive_delete_by_id(self):
        """Create Architecture with valid values then delete it
        by ID

        @feature: Architecture

        @assert: Architecture is deleted
        """
        for name in valid_data_list():
            with self.subTest(name):
                architecture = make_architecture({'name': name})
                Architecture.delete({'id': architecture['id']})
                with self.assertRaises(CLIReturnCodeError):
                    Architecture.info({'id': architecture['id']})

    @tier1
    @run_only_on('sat')
    def test_negative_delete_by_id(self):
        """Create Architecture then delete it by wrong ID

        @feature: Architecture

        @assert: Architecture is not deleted
        """
        for entity_id in invalid_id_list():
            with self.subTest(entity_id):
                with self.assertRaises(CLIReturnCodeError):
                    Architecture.delete({'id': entity_id})
