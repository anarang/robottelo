# -*- encoding: utf-8 -*-
"""Implements GPG keys UI."""

from robottelo.ui.base import Base, UIError
from robottelo.ui.locators import locators, common_locators, tab_locators
from robottelo.ui.navigator import Navigator
from selenium.webdriver.support.select import Select


class GPGKey(Base):
    """Manipulates GPG keys from UI."""
    is_katello = True

    def navigate_to_entity(self):
        """Navigate to GPG key entity page"""
        Navigator(self.browser).go_to_gpg_keys()

    def _search_locator(self):
        """Specify locator for GPG key entity search procedure"""
        return locators['gpgkey.key_name']

    def create(self, name, upload_key=False, key_path=None, key_content=None):
        """Creates a gpg key from UI."""
        self.click(locators['gpgkey.new'])

        if self.wait_until_element(common_locators['name']):
            self.find_element(
                common_locators['name']).send_keys(name)
            if upload_key:
                self.click(locators['gpgkey.upload'])
                self.find_element(
                    locators['gpgkey.file_path']).send_keys(key_path)
            elif key_content:
                self.click(locators['gpgkey.content'])
                self.find_element(
                    locators['gpgkey.content']).send_keys(key_content)
            else:
                raise UIError(
                    u'Could not create new gpgkey "{0}" without contents'
                    .format(name)
                )
            self.click(common_locators['create'])
            self.wait_until_element_is_not_visible(locators['gpgkey.new_form'])
        else:
            raise UIError(
                'Could not create new gpg key "{0}"'.format(name)
            )

    def delete(self, name, really=True):
        """Deletes an existing gpg key."""
        self.delete_entity(
            name,
            really,
            locators['gpgkey.remove'],
        )

    def update(self, name, new_name=None, new_key=None):
        """Updates an existing GPG key."""
        element = self.search(name)
        self.click(element)
        if new_name:
            self.edit_entity(
                locators['gpgkey.edit_name'],
                locators['gpgkey.edit_name_text'],
                new_name,
                locators['gpgkey.save_name']
            )
            self.wait_for_ajax()
        if new_key:
            self.wait_until_element(
                locators['gpgkey.file_path']).send_keys(new_key)
            self.click(locators['gpgkey.upload_button'])

    def assert_product_repo(self, key_name, product):
        """To validate product and repo association with gpg keys.

        Here product is a boolean variable when product = True; validation
        assert product tab otherwise assert repo tab.
        """
        element = self.search(key_name)
        self.click(element)
        if product:
            self.click(tab_locators['gpgkey.tab_products'])
        else:
            self.click(tab_locators['gpgkey.tab_repos'])
        if self.wait_until_element(locators['gpgkey.product_repo']):
            element = self.find_element(
                locators['gpgkey.product_repo']).get_attribute('innerHTML')
            return element.strip(' \t\n\r')

    def assert_key_from_product(self, name, prd_element, repo=None):
        """Assert the key association after deletion from product tab."""
        self.click(prd_element)
        if repo is not None:
            self.click(tab_locators['prd.tab_repos'])
            strategy, value = locators['repo.select']
            self.click((strategy, value % repo))
            self.click(locators['repo.gpg_key_edit'])
            element = Select(
                self.find_element(locators['repo.gpg_key_update'])
            ).first_selected_option.text
            if element != '':
                raise UIError(
                    'GPGKey "{0}" is still assoc with selected repo'
                    .format(name)
                )
        else:
            self.click(tab_locators['prd.tab_details'])
            self.click(locators['prd.gpg_key_edit'])
            element = Select(
                self.find_element(locators['prd.gpg_key_update'])
            ).first_selected_option.text
            if element != '':
                raise UIError(
                    'GPG key "{0}" is still assoc with product'
                    .format(name)
                )
        return None
