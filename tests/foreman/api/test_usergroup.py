"""Unit tests for the ``usergroups`` paths.

Each ``APITestCase`` subclass tests a single URL. A full list of URLs to be
tested can be found here:
http://theforeman.org/api/1.11/apidoc/v2/usergroups.html
"""
from fauxfactory import gen_string
from nailgun import entities
from random import randint
from requests.exceptions import HTTPError
from robottelo.datafactory import (
    invalid_values_list,
    valid_data_list,
    valid_usernames_list,
)
from robottelo.decorators import tier1, tier2
from robottelo.test import APITestCase


class UserGroupTestCase(APITestCase):
    """Tests for the ``usergroups`` path."""

    @tier1
    def test_positive_create_with_name(self):
        """Create new user group using different valid names

        @Feature: Usergroup

        @Assert: User group is created successfully.
        """
        for name in valid_data_list():
            with self.subTest(name):
                user_group = entities.UserGroup(name=name).create()
                self.assertEqual(user_group.name, name)

    @tier1
    def test_positive_create_with_user(self):
        """Create new user group using valid user attached to that group.

        @Feature: Usergroup

        @Assert: User group is created successfully.
        """
        for login in valid_usernames_list():
            with self.subTest(login):
                user = entities.User(login=login).create()
                user_group = entities.UserGroup(user=[user]).create()
                self.assertEqual(len(user_group.user), 1)
                self.assertEqual(user_group.user[0].read().login, login)

    @tier1
    def test_positive_create_with_users(self):
        """Create new user group using multiple users attached to that group.

        @Feature: Usergroup

        @Assert: User group is created successfully and contains all expected
        users.
        """
        users = [entities.User().create() for _ in range(randint(3, 5))]
        user_group = entities.UserGroup(user=users).create()
        self.assertEqual(
            sorted([user.login for user in users]),
            sorted([user.read().login for user in user_group.user])
        )

    @tier1
    def test_positive_create_with_role(self):
        """Create new user group using valid role attached to that group.

        @Feature: Usergroup

        @Assert: User group is created successfully.
        """
        for role_name in valid_data_list():
            with self.subTest(role_name):
                role = entities.Role(name=role_name).create()
                user_group = entities.UserGroup(role=[role]).create()
                self.assertEqual(len(user_group.role), 1)
                self.assertEqual(user_group.role[0].read().name, role_name)

    @tier1
    def test_positive_create_with_roles(self):
        """Create new user group using multiple roles attached to that group.

        @Feature: Usergroup

        @Assert: User group is created successfully and contains all expected
        roles
        """
        roles = [entities.Role().create() for _ in range(randint(3, 5))]
        user_group = entities.UserGroup(role=roles).create()
        self.assertEqual(
            sorted([role.name for role in roles]),
            sorted([role.read().name for role in user_group.role])
        )

    @tier1
    def test_positive_create_with_usergroup(self):
        """Create new user group using another user group attached to the
        initial group.

        @Feature: Usergroup

        @Assert: User group is created successfully.
        """
        for name in valid_data_list():
            with self.subTest(name):
                sub_user_group = entities.UserGroup(name=name).create()
                user_group = entities.UserGroup(
                    usergroup=[sub_user_group],
                ).create()
                self.assertEqual(len(user_group.usergroup), 1)
                self.assertEqual(user_group.usergroup[0].read().name, name)

    @tier2
    def test_positive_create_with_usergroups(self):
        """Create new user group using multiple user groups attached to that
        initial group.

        @Feature: Usergroup

        @Assert: User group is created successfully and contains all expected
        user groups
        """
        sub_user_groups = [
            entities.UserGroup().create() for _ in range(randint(3, 5))]
        user_group = entities.UserGroup(usergroup=sub_user_groups).create()
        self.assertEqual(
            sorted([usergroup.name for usergroup in sub_user_groups]),
            sorted(
                [usergroup.read().name for usergroup in user_group.usergroup])
        )

    @tier1
    def test_negative_create_with_name(self):
        """Attempt to create user group with invalid name.

        @Feature: Usergroup

        @Assert: User group is not created.
        """
        for name in invalid_values_list():
            with self.subTest(name):
                with self.assertRaises(HTTPError):
                    entities.UserGroup(name=name).create()

    @tier1
    def test_negative_create_with_same_name(self):
        """Attempt to create user group with a name of already existent entity.

        @Feature: Usergroup

        @Assert: User group is not created.
        """
        user_group = entities.UserGroup().create()
        with self.assertRaises(HTTPError):
            entities.UserGroup(name=user_group.name).create()

    @tier1
    def test_positive_update(self):
        """Update existing user group with different valid names.

        @Feature: Usergroup

        @Assert: User group is updated successfully.
        """
        user_group = entities.UserGroup().create()
        for new_name in valid_data_list():
            with self.subTest(new_name):
                user_group.name = new_name
                user_group = user_group.update(['name'])
                self.assertEqual(new_name, user_group.name)

    @tier1
    def test_positive_update_with_new_user(self):
        """Add new user to user group

        @Feature: Usergroup

        @Assert: User is added to user group successfully.
        """
        user = entities.User().create()
        user_group = entities.UserGroup().create()
        user_group.user = [user]
        user_group = user_group.update(['user'])
        self.assertEqual(user.login, user_group.user[0].read().login)

    @tier2
    def test_positive_update_with_existing_user(self):
        """Update user that assigned to user group with another one

        @Feature: Usergroup

        @Assert: User group is updated successfully.
        """
        users = [entities.User().create() for _ in range(2)]
        user_group = entities.UserGroup(user=[users[0]]).create()
        user_group.user[0] = users[1]
        user_group = user_group.update(['user'])
        self.assertEqual(users[1].login, user_group.user[0].read().login)

    @tier1
    def test_positive_update_with_new_role(self):
        """Add new role to user group

        @Feature: Usergroup

        @Assert: Role is added to user group successfully.
        """
        new_role = entities.Role().create()
        user_group = entities.UserGroup().create()
        user_group.role = [new_role]
        user_group = user_group.update(['role'])
        self.assertEqual(new_role.name, user_group.role[0].read().name)

    @tier1
    def test_positive_update_with_new_usergroup(self):
        """Add new user group to existing one

        @Feature: Usergroup

        @Assert: User group is added to existing group successfully.
        """
        new_usergroup = entities.UserGroup().create()
        user_group = entities.UserGroup().create()
        user_group.usergroup = [new_usergroup]
        user_group = user_group.update(['usergroup'])
        self.assertEqual(
            new_usergroup.name, user_group.usergroup[0].read().name)

    @tier1
    def test_negative_update(self):
        """Attempt to update existing user group using different invalid names.

        @Feature: Usergroup

        @Assert: User group is not updated.
        """
        user_group = entities.UserGroup().create()
        for new_name in invalid_values_list():
            with self.subTest(new_name):
                user_group.name = new_name
                with self.assertRaises(HTTPError):
                    user_group.update(['name'])
                self.assertNotEqual(user_group.read().name, new_name)

    @tier1
    def test_negative_update_with_same_name(self):
        """Attempt to update user group with a name of already existent entity.

        @Feature: Usergroup

        @Assert: User group is not updated.
        """
        name = gen_string('alphanumeric')
        entities.UserGroup(name=name).create()
        new_user_group = entities.UserGroup().create()
        new_user_group.name = name
        with self.assertRaises(HTTPError):
            new_user_group.update(['name'])
        self.assertNotEqual(new_user_group.read().name, name)

    @tier1
    def test_positive_delete(self):
        """Create user group with valid name and then delete it

        @feature: Usergroup

        @assert: User group is deleted successfully
        """
        user_group = entities.UserGroup().create()
        user_group.delete()
        with self.assertRaises(HTTPError):
            user_group.read()
