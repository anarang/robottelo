# -*- encoding: utf-8 -*-
"""Unit tests for the Docker feature."""
from fauxfactory import gen_choice, gen_string, gen_url
from nailgun import entities
from random import randint, shuffle
from requests.exceptions import HTTPError
from robottelo.api.utils import promote
from robottelo.config import settings
from robottelo.constants import (
    DOCKER_REGISTRY_HUB,
    DOCKER_0_EXTERNAL_REGISTRY,
    DOCKER_1_EXTERNAL_REGISTRY,
)
from robottelo.datafactory import valid_data_list
from robottelo.decorators import (
    run_only_on,
    skip_if_bug_open,
    skip_if_not_set,
    stubbed,
    tier1,
    tier2,
)
from robottelo.helpers import install_katello_ca, remove_katello_ca
from robottelo.test import APITestCase

DOCKER_PROVIDER = 'Docker'
STRING_TYPES = ['alpha', 'alphanumeric', 'cjk', 'utf8', 'latin1']


def _invalid_names():
    """Return a generator yielding various kinds of invalid strings for
    Docker repositories.

    """
    return (
        # boundaries
        gen_string('alphanumeric', 2),
        gen_string('alphanumeric', 31),
        u'{0}/{1}'.format(
            gen_string('alphanumeric', 3),
            gen_string('alphanumeric', 3)
        ),
        u'{0}/{1}'.format(
            gen_string('alphanumeric', 4),
            gen_string('alphanumeric', 2)
        ),
        u'{0}/{1}'.format(
            gen_string('alphanumeric', 31),
            gen_string('alphanumeric', 30)
        ),
        u'{0}/{1}'.format(
            gen_string('alphanumeric', 30),
            gen_string('alphanumeric', 31)
        ),
        # not allowed non alphanumeric character
        u'{0}+{1}_{2}/{2}-{1}_{0}.{3}'.format(
            gen_string('alphanumeric', randint(3, 6)),
            gen_string('alphanumeric', randint(3, 6)),
            gen_string('alphanumeric', randint(3, 6)),
            gen_string('alphanumeric', randint(3, 6)),
        ),
        u'{0}-{1}_{2}/{2}+{1}_{0}.{3}'.format(
            gen_string('alphanumeric', randint(3, 6)),
            gen_string('alphanumeric', randint(3, 6)),
            gen_string('alphanumeric', randint(3, 6)),
            gen_string('alphanumeric', randint(3, 6)),
        ),
    )


def _valid_names():
    """Return a generator yielding various kinds of valid strings for
    Docker repositories.

    """
    return (
        # boundaries
        gen_string('alphanumeric', 3).lower(),
        gen_string('alphanumeric', 30).lower(),
        u'{0}/{1}'.format(
            gen_string('alphanumeric', 4).lower(),
            gen_string('alphanumeric', 3).lower(),
        ),
        u'{0}/{1}'.format(
            gen_string('alphanumeric', 30).lower(),
            gen_string('alphanumeric', 30).lower(),
        ),
        # allowed non alphanumeric character
        u'{0}-{1}_{2}/{2}-{1}_{0}.{3}'.format(
            gen_string('alphanumeric', randint(3, 6)).lower(),
            gen_string('alphanumeric', randint(3, 6)).lower(),
            gen_string('alphanumeric', randint(3, 6)).lower(),
            gen_string('alphanumeric', randint(3, 6)).lower(),
        ),
        u'-_-_/-_.',
    )


def _create_repository(product, name=None, upstream_name=None):
    """Creates a Docker-based repository.

    :param product: A ``Product`` object.
    :param str name: Name for the repository. If ``None`` then a random
        value will be generated.
    :param str upstream_name: A valid name of an existing upstream repository.
        If ``None`` then defaults to ``busybox``.
    :return: A ``Repository`` object.

    """
    if name is None:
        name = gen_string(gen_choice(STRING_TYPES), 15)
    if upstream_name is None:
        upstream_name = u'busybox'
    return entities.Repository(
        content_type=u'docker',
        docker_upstream_name=upstream_name,
        name=name,
        product=product,
        url=DOCKER_REGISTRY_HUB,
    ).create()


class DockerRepositoryTestCase(APITestCase):
    """Tests specific to performing CRUD methods against ``Docker``
    repositories.

    """

    @classmethod
    def setUpClass(cls):
        """Create an organization and product which can be re-used in tests."""
        super(DockerRepositoryTestCase, cls).setUpClass()
        cls.org = entities.Organization().create()

    @tier1
    @run_only_on('sat')
    def test_positive_create_with_name(self):
        """Create one Docker-type repository

        @Assert: A repository is created with a Docker upstream repository.

        @Feature: Docker
        """
        for name in valid_data_list():
            with self.subTest(name):
                repo = _create_repository(
                    entities.Product(organization=self.org).create(),
                    name,
                )
                self.assertEqual(repo.name, name)
                self.assertEqual(repo.docker_upstream_name, 'busybox')
                self.assertEqual(repo.content_type, 'docker')

    @tier1
    @run_only_on('sat')
    def test_positive_create_with_upstream_name(self):
        """Create a Docker-type repository with a valid docker upstream
        name

        @Assert: A repository is created with the specified upstream name.

        @Feature: Docker
        """
        for upstream_name in _valid_names():
            with self.subTest(upstream_name):
                repo = _create_repository(
                    entities.Product(organization=self.org).create(),
                    upstream_name=upstream_name,
                )
                self.assertEqual(repo.docker_upstream_name, upstream_name)
                self.assertEqual(repo.content_type, u'docker')

    @tier1
    @run_only_on('sat')
    def test_negative_create_with_invalid_upstream_name(self):
        """Create a Docker-type repository with a invalid docker
        upstream name.

        @Assert: A repository is not created and a proper error is raised.

        @Feature: Docker
        """
        product = entities.Product(organization=self.org).create()
        for upstream_name in _invalid_names():
            with self.subTest(upstream_name):
                with self.assertRaises(HTTPError):
                    _create_repository(product, upstream_name=upstream_name)

    @tier2
    @run_only_on('sat')
    def test_positive_create_repos_using_same_product(self):
        """Create multiple Docker-type repositories

        @Assert: Multiple docker repositories are created with a Docker
        usptream repository and they all belong to the same product.

        @Feature: Docker
        """
        product = entities.Product(organization=self.org).create()
        for _ in range(randint(2, 5)):
            repo = _create_repository(product)
            product = product.read()
            self.assertIn(repo.id, [repo_.id for repo_ in product.repository])

    @tier2
    @run_only_on('sat')
    def test_positive_create_repos_using_multiple_products(self):
        """Create multiple Docker-type repositories on multiple products

        @Assert: Multiple docker repositories are created with a Docker
        upstream repository and they all belong to their respective products.

        @Feature: Docker
        """
        for _ in range(randint(2, 5)):
            product = entities.Product(organization=self.org).create()
            for _ in range(randint(2, 3)):
                repo = _create_repository(product)
                product = product.read()
                self.assertIn(
                    repo.id,
                    [repo_.id for repo_ in product.repository],
                )

    @tier2
    @run_only_on('sat')
    def test_positive_sync(self):
        """Create and sync a Docker-type repository

        @Assert: A repository is created with a Docker repository
        and it is synchronized.

        @Feature: Docker
        """
        repo = _create_repository(
            entities.Product(organization=self.org).create()
        )
        repo.sync()
        repo = repo.read()
        self.assertGreaterEqual(repo.content_counts['docker_manifest'], 1)

    @tier1
    @run_only_on('sat')
    def test_positive_update_name(self):
        """Create a Docker-type repository and update its name.

        @Assert: A repository is created with a Docker upstream repository and
        that its name can be updated.

        @Feature: Docker
        """
        repo = _create_repository(
            entities.Product(organization=self.org).create())

        # Update the repository name to random value
        for new_name in valid_data_list():
            with self.subTest(new_name):
                repo.name = new_name
                repo = repo.update()
                self.assertEqual(repo.name, new_name)

    @tier1
    @run_only_on('sat')
    def test_positive_update_upstream_name(self):
        """Create a Docker-type repository and update its upstream name.

        @Assert: A repository is created with a Docker upstream repository and
        that its upstream name can be updated.

        @Feature: Docker
        """
        new_upstream_name = u'fedora/ssh'
        repo = _create_repository(
            entities.Product(organization=self.org).create())
        self.assertNotEqual(repo.docker_upstream_name, new_upstream_name)

        # Update the repository upstream name
        repo.docker_upstream_name = new_upstream_name
        repo = repo.update()
        self.assertEqual(repo.docker_upstream_name, new_upstream_name)

    @tier2
    @run_only_on('sat')
    def test_positive_update_url(self):
        """Create a Docker-type repository and update its URL.

        @Assert: A repository is created with a Docker upstream repository and
        that its URL can be updated.

        @Feature: Docker
        """
        new_url = gen_url()
        repo = _create_repository(
            entities.Product(organization=self.org).create())
        self.assertEqual(repo.url, DOCKER_REGISTRY_HUB)

        # Update the repository URL
        repo.url = new_url
        repo = repo.update()
        self.assertEqual(repo.url, new_url)
        self.assertNotEqual(repo.url, DOCKER_REGISTRY_HUB)

    @tier1
    @run_only_on('sat')
    def test_positive_delete(self):
        """Create and delete a Docker-type repository

        @Assert: A repository is created with a Docker upstream repository and
        then deleted.

        @Feature: Docker
        """
        repo = _create_repository(
            entities.Product(organization=self.org).create())
        # Delete it
        repo.delete()
        with self.assertRaises(HTTPError):
            repo.read()

    @tier2
    @run_only_on('sat')
    def test_positive_delete_random_repo(self):
        """Create Docker-type repositories on multiple products and
        delete a random repository from a random product.

        @Assert: Random repository can be deleted from random product without
        altering the other products.

        @Feature: Docker
        """
        repos = []
        products = [
            entities.Product(organization=self.org).create()
            for _
            in range(randint(2, 5))
        ]
        for product in products:
            repo = _create_repository(product)
            self.assertEqual(repo.content_type, u'docker')
            repos.append(repo)

        # Delete a random repository
        shuffle(repos)
        repo = repos.pop()
        repo.delete()
        with self.assertRaises(HTTPError):
            repo.read()

        # Check if others repositories are not touched
        for repo in repos:
            repo = repo.read()
            self.assertIn(repo.product.id, [prod.id for prod in products])


class DockerContentViewTestCase(APITestCase):
    """Tests specific to using ``Docker`` repositories with Content Views."""

    @classmethod
    def setUpClass(cls):
        """Create an organization which can be re-used in tests."""
        super(DockerContentViewTestCase, cls).setUpClass()
        cls.org = entities.Organization().create()

    @tier2
    @run_only_on('sat')
    def test_positive_add_docker_repo(self):
        """Add one Docker-type repository to a non-composite content view

        @Assert: A repository is created with a Docker repository and the
        product is added to a non-composite content view

        @Feature: Docker
        """
        repo = _create_repository(
            entities.Product(organization=self.org).create())
        # Create content view and associate docker repo
        content_view = entities.ContentView(
            composite=False,
            organization=self.org,
        ).create()
        content_view.repository = [repo]
        content_view = content_view.update(['repository'])
        self.assertIn(repo.id, [repo_.id for repo_ in content_view.repository])

    @tier2
    @run_only_on('sat')
    def test_positive_add_docker_repos(self):
        """Add multiple Docker-type repositories to a
        non-composite content view.

        @Assert: Repositories are created with Docker upstream repos and the
        product is added to a non-composite content view.

        @Feature: Docker
        """
        product = entities.Product(organization=self.org).create()
        repos = [
            _create_repository(product, name=gen_string('alpha'))
            for _
            in range(randint(2, 5))
        ]
        self.assertEqual(len(product.read().repository), len(repos))

        content_view = entities.ContentView(
            composite=False,
            organization=self.org,
        ).create()
        content_view.repository = repos
        content_view = content_view.update(['repository'])

        self.assertEqual(len(content_view.repository), len(repos))

        content_view.repository = [
            repo.read() for repo in content_view.repository
        ]

        self.assertEqual(
            {repo.id for repo in repos},
            {repo.id for repo in content_view.repository}
        )

        for repo in repos + content_view.repository:
            self.assertEqual(repo.content_type, u'docker')
            self.assertEqual(repo.docker_upstream_name, u'busybox')

    @tier2
    @run_only_on('sat')
    def test_positive_add_synced_docker_repo(self):
        """Create and sync a Docker-type repository

        @Assert: A repository is created with a Docker repository
        and it is synchronized.

        @Feature: Docker
        """
        repo = _create_repository(
            entities.Product(organization=self.org).create())
        repo.sync()
        repo = repo.read()
        self.assertGreaterEqual(repo.content_counts['docker_manifest'], 1)

        # Create content view and associate docker repo
        content_view = entities.ContentView(
            composite=False,
            organization=self.org,
        ).create()
        content_view.repository = [repo]
        content_view = content_view.update(['repository'])
        self.assertIn(repo.id, [repo_.id for repo_ in content_view.repository])

    @tier2
    @run_only_on('sat')
    def test_positive_add_docker_repo_to_ccv(self):
        """Add one Docker-type repository to a composite content view

        @Assert: A repository is created with a Docker repository and the
        product is added to a content view which is then added to a composite
        content view.

        @Feature: Docker
        """
        repo = _create_repository(
            entities.Product(organization=self.org).create())

        # Create content view and associate docker repo
        content_view = entities.ContentView(
            composite=False,
            organization=self.org,
        ).create()
        content_view.repository = [repo]
        content_view = content_view.update(['repository'])
        self.assertIn(repo.id, [repo_.id for repo_ in content_view.repository])

        # Publish it and grab its version ID (there should only be one version)
        content_view.publish()
        content_view = content_view.read()
        self.assertEqual(len(content_view.version), 1)

        # Create composite content view and associate content view to it
        comp_content_view = entities.ContentView(
            composite=True,
            organization=self.org,
        ).create()
        comp_content_view.component = content_view.version
        comp_content_view = comp_content_view.update(['component'])
        self.assertIn(
            content_view.version[0].id,
            [component.id for component in comp_content_view.component]
        )

    @tier2
    @run_only_on('sat')
    def test_positive_add_docker_repos_to_ccv(self):
        """Add multiple Docker-type repositories to a composite
        content view.

        @Assert: One repository is created with a Docker upstream repository
        and the product is added to a random number of content views which are
        then added to a composite content view.

        @Feature: Docker
        """
        cv_versions = []
        product = entities.Product(organization=self.org).create()
        for _ in range(randint(2, 5)):
            # Create content view and associate docker repo
            content_view = entities.ContentView(
                composite=False,
                organization=self.org,
            ).create()
            repo = _create_repository(product)
            content_view.repository = [repo]
            content_view = content_view.update(['repository'])
            self.assertIn(
                repo.id,
                [repo_.id for repo_ in content_view.repository]
            )

            # Publish it and grab its version ID (there should be one version)
            content_view.publish()
            content_view = content_view.read()
            cv_versions.append(content_view.version[0])

        # Create composite content view and associate content view to it
        comp_content_view = entities.ContentView(
            composite=True,
            organization=self.org,
        ).create()
        for cv_version in cv_versions:
            comp_content_view.component.append(cv_version)
            comp_content_view = comp_content_view.update(['component'])
            self.assertIn(
                cv_version.id,
                [component.id for component in comp_content_view.component]
            )

    @tier2
    @run_only_on('sat')
    def test_positive_publish_with_docker_repo(self):
        """Add Docker-type repository to content view and publish it once.

        @Assert: One repository is created with a Docker upstream repository
        and the product is added to a content view which is then published
        only once.

        @Feature: Docker
        """
        repo = _create_repository(
            entities.Product(organization=self.org).create())

        content_view = entities.ContentView(
            composite=False,
            organization=self.org,
        ).create()
        content_view.repository = [repo]
        content_view = content_view.update(['repository'])
        self.assertIn(repo.id, [repo_.id for repo_ in content_view.repository])

        # Not published yet?
        content_view = content_view.read()
        self.assertIsNone(content_view.last_published)
        self.assertEqual(content_view.next_version, 1)

        # Publish it and check that it was indeed published.
        content_view.publish()
        content_view = content_view.read()
        self.assertIsNotNone(content_view.last_published)
        self.assertGreater(content_view.next_version, 1)

    @tier2
    @run_only_on('sat')
    @skip_if_bug_open('bugzilla', 1217635)
    def test_positive_publish_with_docker_repo_composite(self):
        """Add Docker-type repository to composite content view and
        publish it once.

        @Assert: One repository is created with an upstream repository and the
        product is added to a content view which is then published only once
        and then added to a composite content view which is also published only
        once.

        @Feature: Docker
        """
        repo = _create_repository(
            entities.Product(organization=self.org).create())
        content_view = entities.ContentView(
            composite=False,
            organization=self.org,
        ).create()
        content_view.repository = [repo]
        content_view = content_view.update(['repository'])
        self.assertIn(repo.id, [repo_.id for repo_ in content_view.repository])

        # Not published yet?
        content_view = content_view.read()
        self.assertIsNone(content_view.last_published)
        self.assertEqual(content_view.next_version, 1)

        # Publish it and check that it was indeed published.
        content_view.publish()
        content_view = content_view.read()
        self.assertIsNotNone(content_view.last_published)
        self.assertGreater(content_view.next_version, 1)

        # Create composite content view…
        comp_content_view = entities.ContentView(
            composite=True,
            organization=self.org,
        ).create()
        comp_content_view.component = [content_view.version[0]]
        comp_content_view = comp_content_view.update(['component'])
        self.assertIn(
            content_view.version[0].id,  # pylint:disable=no-member
            [component.id for component in comp_content_view.component]
        )
        # … publish it…
        comp_content_view.publish()
        # … and check that it was indeed published
        comp_content_view = comp_content_view.read()
        self.assertIsNotNone(comp_content_view.last_published)
        self.assertGreater(comp_content_view.next_version, 1)

    @tier2
    @run_only_on('sat')
    def test_positive_publish_multiple_with_docker_repo(self):
        """Add Docker-type repository to content view and publish it
        multiple times.

        @Assert: One repository is created with a Docker upstream repository
        and the product is added to a content view which is then published
        multiple times.

        @Feature: Docker
        """
        repo = _create_repository(
            entities.Product(organization=self.org).create())
        content_view = entities.ContentView(
            composite=False,
            organization=self.org,
        ).create()
        content_view.repository = [repo]
        content_view = content_view.update(['repository'])
        self.assertEqual(
            [repo.id], [repo_.id for repo_ in content_view.repository])
        self.assertIsNone(content_view.read().last_published)

        publish_amount = randint(2, 5)
        for _ in range(publish_amount):
            content_view.publish()
        content_view = content_view.read()
        self.assertIsNotNone(content_view.last_published)
        self.assertEqual(len(content_view.version), publish_amount)

    @tier2
    @run_only_on('sat')
    def test_positive_publish_multiple_with_docker_repo_composite(self):
        """Add Docker-type repository to content view and publish it
        multiple times.

        @Assert: One repository is created with a Docker upstream repository
        and the product is added to a content view which is then added to a
        composite content view which is then published multiple times.

        @Feature: Docker
        """
        repo = _create_repository(
            entities.Product(organization=self.org).create())
        content_view = entities.ContentView(
            composite=False,
            organization=self.org,
        ).create()
        content_view.repository = [repo]
        content_view = content_view.update(['repository'])
        self.assertEqual(
            [repo.id], [repo_.id for repo_ in content_view.repository])
        self.assertIsNone(content_view.read().last_published)

        content_view.publish()
        content_view = content_view.read()
        self.assertIsNotNone(content_view.last_published)

        comp_content_view = entities.ContentView(
            composite=True,
            organization=self.org,
        ).create()
        comp_content_view.component = [content_view.version[0]]
        comp_content_view = comp_content_view.update(['component'])
        self.assertEqual(
            [content_view.version[0].id],
            [comp.id for comp in comp_content_view.component],
        )
        self.assertIsNone(comp_content_view.last_published)

        publish_amount = randint(2, 5)
        for _ in range(publish_amount):
            comp_content_view.publish()
        comp_content_view = comp_content_view.read()
        self.assertIsNotNone(comp_content_view.last_published)
        self.assertEqual(len(comp_content_view.version), publish_amount)

    @tier2
    @run_only_on('sat')
    def test_positive_promote_with_docker_repo(self):
        """Add Docker-type repository to content view and publish it.
        Then promote it to the next available lifecycle-environment.

        @Assert: Docker-type repository is promoted to content view found in
        the specific lifecycle-environment.

        @Feature: Docker
        """
        lce = entities.LifecycleEnvironment(organization=self.org).create()
        repo = _create_repository(
            entities.Product(organization=self.org).create())

        content_view = entities.ContentView(
            composite=False,
            organization=self.org,
        ).create()
        content_view.repository = [repo]
        content_view = content_view.update(['repository'])
        self.assertEqual(
            [repo.id], [repo_.id for repo_ in content_view.repository])

        content_view.publish()
        content_view = content_view.read()
        cvv = content_view.version[0].read()
        self.assertEqual(len(cvv.environment), 1)

        promote(cvv, lce.id)
        self.assertEqual(len(cvv.read().environment), 2)

    @tier2
    @run_only_on('sat')
    def test_positive_promote_multiple_with_docker_repo(self):
        """Add Docker-type repository to content view and publish it.
        Then promote it to multiple available lifecycle-environments.

        @Assert: Docker-type repository is promoted to content view found in
        the specific lifecycle-environments.

        @Feature: Docker
        """
        repo = _create_repository(
            entities.Product(organization=self.org).create())

        content_view = entities.ContentView(
            composite=False,
            organization=self.org,
        ).create()
        content_view.repository = [repo]
        content_view = content_view.update(['repository'])
        self.assertEqual(
            [repo.id], [repo_.id for repo_ in content_view.repository])

        content_view.publish()
        cvv = content_view.read().version[0]
        self.assertEqual(len(cvv.read().environment), 1)

        for i in range(1, randint(3, 6)):
            lce = entities.LifecycleEnvironment(organization=self.org).create()
            promote(cvv, lce.id)
            self.assertEqual(len(cvv.read().environment), i+1)

    @tier2
    @run_only_on('sat')
    def test_positive_promote_with_docker_repo_composite(self):
        """Add Docker-type repository to content view and publish it.
        Then add that content view to composite one. Publish and promote that
        composite content view to the next available lifecycle-environment.

        @Assert: Docker-type repository is promoted to content view found in
        the specific lifecycle-environment.

        @Feature: Docker
        """
        lce = entities.LifecycleEnvironment(organization=self.org).create()
        repo = _create_repository(
            entities.Product(organization=self.org).create())
        content_view = entities.ContentView(
            composite=False,
            organization=self.org,
        ).create()
        content_view.repository = [repo]
        content_view = content_view.update(['repository'])
        self.assertEqual(
            [repo.id], [repo_.id for repo_ in content_view.repository])

        content_view.publish()
        cvv = content_view.read().version[0].read()

        comp_content_view = entities.ContentView(
            composite=True,
            organization=self.org,
        ).create()
        comp_content_view.component = [cvv]
        comp_content_view = comp_content_view.update(['component'])
        self.assertEqual(cvv.id, comp_content_view.component[0].id)

        comp_content_view.publish()
        comp_cvv = comp_content_view.read().version[0]
        self.assertEqual(len(comp_cvv.read().environment), 1)

        promote(comp_cvv, lce.id)
        self.assertEqual(len(comp_cvv.read().environment), 2)

    @tier2
    @run_only_on('sat')
    def test_positive_promote_multiple_with_docker_repo_composite(self):
        """Add Docker-type repository to content view and publish it.
        Then add that content view to composite one. Publish and promote that
        composite content view to the multiple available lifecycle-environments

        @Assert: Docker-type repository is promoted to content view found in
        the specific lifecycle-environments.

        @Feature: Docker
        """
        repo = _create_repository(
            entities.Product(organization=self.org).create())
        content_view = entities.ContentView(
            composite=False,
            organization=self.org,
        ).create()
        content_view.repository = [repo]
        content_view = content_view.update(['repository'])
        self.assertEqual(
            [repo.id], [repo_.id for repo_ in content_view.repository])

        content_view.publish()
        cvv = content_view.read().version[0].read()

        comp_content_view = entities.ContentView(
            composite=True,
            organization=self.org,
        ).create()
        comp_content_view.component = [cvv]
        comp_content_view = comp_content_view.update(['component'])
        self.assertEqual(cvv.id, comp_content_view.component[0].id)

        comp_content_view.publish()
        comp_cvv = comp_content_view.read().version[0]
        self.assertEqual(len(comp_cvv.read().environment), 1)

        for i in range(1, randint(3, 6)):
            lce = entities.LifecycleEnvironment(organization=self.org).create()
            promote(comp_cvv, lce.id)
            self.assertEqual(len(comp_cvv.read().environment), i+1)


class DockerActivationKeyTestCase(APITestCase):
    """Tests specific to adding ``Docker`` repositories to Activation Keys."""

    @classmethod
    def setUpClass(cls):
        """Create necessary objects which can be re-used in tests."""
        super(DockerActivationKeyTestCase, cls).setUpClass()
        cls.org = entities.Organization().create()
        cls.lce = entities.LifecycleEnvironment(organization=cls.org).create()
        cls.repo = _create_repository(
            entities.Product(organization=cls.org).create())
        content_view = entities.ContentView(
            composite=False,
            organization=cls.org,
        ).create()
        content_view.repository = [cls.repo]
        cls.content_view = content_view.update(['repository'])
        cls.content_view.publish()
        cls.cvv = content_view.read().version[0].read()
        promote(cls.cvv, cls.lce.id)

    @tier2
    @run_only_on('sat')
    def test_positive_add_docker_repo_cv(self):
        """Add Docker-type repository to a non-composite content view
        and publish it. Then create an activation key and associate it with the
        Docker content view.

        @Assert: Docker-based content view can be added to activation key

        @Feature: Docker
        """
        ak = entities.ActivationKey(
            content_view=self.content_view,
            environment=self.lce,
            organization=self.org,
        ).create()
        self.assertEqual(ak.content_view.id, self.content_view.id)
        self.assertEqual(ak.content_view.read().repository[0].id, self.repo.id)

    @tier2
    @run_only_on('sat')
    def test_positive_remove_docker_repo_cv(self):
        """Add Docker-type repository to a non-composite content view
        and publish it. Create an activation key and associate it with the
        Docker content view. Then remove this content view from the activation
        key.

        @Assert: Docker-based content view can be added and then removed from
        the activation key.

        @Feature: Docker
        """
        ak = entities.ActivationKey(
            content_view=self.content_view,
            environment=self.lce,
            organization=self.org,
        ).create()
        self.assertEqual(ak.content_view.id, self.content_view.id)
        ak.content_view = None
        self.assertIsNone(ak.update(['content_view']).content_view)

    @tier2
    @run_only_on('sat')
    def test_positive_add_docker_repo_ccv(self):
        """Add Docker-type repository to a non-composite content view and
        publish it. Then add this content view to a composite content view and
        publish it. Create an activation key and associate it with the
        composite Docker content view.

        @Assert: Docker-based content view can be added to activation key

        @Feature: Docker
        """
        comp_content_view = entities.ContentView(
            composite=True,
            organization=self.org,
        ).create()
        comp_content_view.component = [self.cvv]
        comp_content_view = comp_content_view.update(['component'])
        self.assertEqual(self.cvv.id, comp_content_view.component[0].id)

        comp_content_view.publish()
        comp_cvv = comp_content_view.read().version[0].read()
        promote(comp_cvv, self.lce.id)

        ak = entities.ActivationKey(
            content_view=comp_content_view,
            environment=self.lce,
            organization=self.org,
        ).create()
        self.assertEqual(ak.content_view.id, comp_content_view.id)

    @tier2
    @run_only_on('sat')
    def test_positive_remove_docker_repo_ccv(self):
        """Add Docker-type repository to a non-composite content view
        and publish it. Then add this content view to a composite content view
        and publish it. Create an activation key and associate it with the
        composite Docker content view. Then, remove the composite content view
        from the activation key.

        @Assert: Docker-based composite content view can be added and then
        removed from the activation key.

        @Feature: Docker
        """
        comp_content_view = entities.ContentView(
            composite=True,
            organization=self.org,
        ).create()
        comp_content_view.component = [self.cvv]
        comp_content_view = comp_content_view.update(['component'])
        self.assertEqual(self.cvv.id, comp_content_view.component[0].id)

        comp_content_view.publish()
        comp_cvv = comp_content_view.read().version[0].read()
        promote(comp_cvv, self.lce.id)

        ak = entities.ActivationKey(
            content_view=comp_content_view,
            environment=self.lce,
            organization=self.org,
        ).create()
        self.assertEqual(ak.content_view.id, comp_content_view.id)
        ak.content_view = None
        self.assertIsNone(ak.update(['content_view']).content_view)


class DockerComputeResourceTestCase(APITestCase):
    """Tests specific to managing Docker-based Compute Resources."""

    @classmethod
    @skip_if_not_set('docker')
    def setUpClass(cls):
        """Create an organization and product which can be re-used in tests."""
        super(DockerComputeResourceTestCase, cls).setUpClass()
        cls.org = entities.Organization().create()

    @tier2
    @run_only_on('sat')
    def test_positive_create_internal(self):
        """Create a Docker-based Compute Resource in the Satellite 6
        instance.

        @Assert: Compute Resource can be created and listed.

        @Feature: Docker
        """
        for name in valid_data_list():
            with self.subTest(name):
                compute_resource = entities.DockerComputeResource(
                    name=name,
                    url=settings.docker.get_unix_socket_url(),
                ).create()
                self.assertEqual(compute_resource.name, name)
                self.assertEqual(compute_resource.provider, DOCKER_PROVIDER)
                self.assertEqual(
                    compute_resource.url,
                    settings.docker.get_unix_socket_url()
                )

    @tier2
    @run_only_on('sat')
    def test_positive_update_internal(self):
        """Create a Docker-based Compute Resource in the Satellite 6
        instance then edit its attributes.

        @Assert: Compute Resource can be created, listed and its attributes can
        be updated.

        @Feature: Docker
        """
        for url in (settings.docker.external_url,
                    settings.docker.get_unix_socket_url()):
            with self.subTest(url):
                compute_resource = entities.DockerComputeResource(
                    organization=[self.org],
                    url=url,
                ).create()
                self.assertEqual(compute_resource.url, url)
                compute_resource.url = gen_url()
                self.assertEqual(
                    compute_resource.url,
                    compute_resource.update(['url']).url,
                )

    @tier2
    @run_only_on('sat')
    def test_positive_list_containers_internal(self):
        """Create a Docker-based Compute Resource in the Satellite 6
        instance then list its running containers.

        @Assert: Compute Resource can be created and existing instances can be
        listed.

        @Feature: Docker
        """
        for url in (settings.docker.external_url,
                    settings.docker.get_unix_socket_url()):
            with self.subTest(url):
                compute_resource = entities.DockerComputeResource(
                    organization=[self.org],
                    url=url,
                ).create()
                self.assertEqual(compute_resource.url, url)
                self.assertEqual(len(entities.AbstractDockerContainer(
                    compute_resource=compute_resource).search()), 0)
                container = entities.DockerHubContainer(
                    command='top',
                    compute_resource=compute_resource,
                    organization=[self.org],
                ).create()
                result = entities.AbstractDockerContainer(
                    compute_resource=compute_resource).search()
                self.assertEqual(len(result), 1)
                self.assertEqual(result[0].name, container.name)

    @tier2
    @run_only_on('sat')
    def test_positive_create_external(self):
        """Create a Docker-based Compute Resource using an external
        Docker-enabled system.

        @Assert: Compute Resource can be created and listed.

        @Feature: Docker
        """
        for name in valid_data_list():
            with self.subTest(name):
                compute_resource = entities.DockerComputeResource(
                    name=name,
                    url=settings.docker.external_url,
                ).create()
                self.assertEqual(compute_resource.name, name)
                self.assertEqual(compute_resource.provider, DOCKER_PROVIDER)
                self.assertEqual(
                    compute_resource.url, settings.docker.external_url)

    @tier1
    @run_only_on('sat')
    def test_positive_delete(self):
        """Create a Docker-based Compute Resource then delete it.

        @Assert: Compute Resource can be created, listed and deleted.

        @Feature: Docker
        """
        for url in (settings.docker.external_url,
                    settings.docker.get_unix_socket_url()):
            with self.subTest(url):
                resource = entities.DockerComputeResource(url=url).create()
                self.assertEqual(resource.url, url)
                self.assertEqual(resource.provider, DOCKER_PROVIDER)
                resource.delete()
                with self.assertRaises(HTTPError):
                    resource.read()


class DockerContainerTestCase(APITestCase):
    """Tests specific to using ``Containers`` in local and external Docker
    Compute Resources

    """

    @classmethod
    @skip_if_not_set('docker')
    def setUpClass(cls):
        """Create an organization and product which can be re-used in tests."""
        super(DockerContainerTestCase, cls).setUpClass()
        cls.org = entities.Organization().create()
        cls.cr_internal = entities.DockerComputeResource(
            name=gen_string('alpha'),
            organization=[cls.org],
            url=settings.docker.get_unix_socket_url(),
        ).create()
        cls.cr_external = entities.DockerComputeResource(
            name=gen_string('alpha'),
            organization=[cls.org],
            url=settings.docker.external_url,
        ).create()
        install_katello_ca()

    @classmethod
    def tearDownClass(cls):
        """Remove katello-ca certificate"""
        remove_katello_ca()
        super(DockerContainerTestCase, cls).tearDownClass()

    @tier2
    @run_only_on('sat')
    def test_positive_create_with_compresource(self):
        """Create containers for local and external compute resources

        @Feature: Docker

        @Assert: The docker container is created for each compute resource
        """
        for compute_resource in (self.cr_internal, self.cr_external):
            with self.subTest(compute_resource.url):
                container = entities.DockerHubContainer(
                    command='top',
                    compute_resource=compute_resource,
                    organization=[self.org],
                ).create()
                self.assertEqual(
                    container.compute_resource.read().name,
                    compute_resource.name,
                )

    @tier2
    @run_only_on('sat')
    @skip_if_bug_open('bugzilla', 1282431)
    def test_positive_create_using_cv(self):
        """Create docker container using custom content view, lifecycle
        environment and docker repository for local and external compute
        resources

        @Feature: Docker

        @Assert: The docker container is created for each compute resource
        """
        lce = entities.LifecycleEnvironment(organization=self.org).create()
        repo = _create_repository(
            entities.Product(organization=self.org).create(),
            upstream_name='centos',
        )
        repo.sync()
        content_view = entities.ContentView(organization=self.org).create()
        content_view.repository = [repo]
        content_view = content_view.update(['repository'])
        content_view.publish()
        content_view = content_view.read()
        self.assertEqual(len(content_view.version), 1)
        cvv = content_view.read().version[0].read()
        promote(cvv, lce.id)
        for compute_resource in (self.cr_internal, self.cr_external):
            with self.subTest(compute_resource):
                container = entities.DockerHubContainer(
                    command='top',
                    compute_resource=compute_resource,
                    organization=[self.org],
                    repository_name=repo.container_repository_name,
                    tag='latest',
                    tty='yes',
                ).create()
                self.assertEqual(
                    container.compute_resource.read().name,
                    compute_resource.name
                )
                self.assertEqual(
                    container.repository_name,
                    repo.container_repository_name
                )
                self.assertEqual(container.tag, 'latest')

    @tier2
    @run_only_on('sat')
    def test_positive_power_on_off(self):
        """Create containers for local and external compute resource,
        then power them on and finally power them off

        @Feature: Docker

        @Assert: The docker container is created for each compute resource
        and the power status is showing properly
        """
        for compute_resource in (self.cr_internal, self.cr_external):
            with self.subTest(compute_resource):
                container = entities.DockerHubContainer(
                    command='top',
                    compute_resource=compute_resource,
                    organization=[self.org],
                ).create()
                self.assertEqual(
                    container.compute_resource.read().url,
                    compute_resource.url,
                )
                self.assertTrue(container.power(
                    data={u'power_action': 'status'})['running'])
                container.power(data={u'power_action': 'stop'})
                self.assertFalse(container.power(
                    data={u'power_action': 'status'})['running'])

    @tier2
    @run_only_on('sat')
    def test_positive_read_container_log(self):
        """Create containers for local and external compute resource and
        read their logs

        @Feature: Docker

        @Assert: The docker container is created for each compute resource and
        its log can be read
        """
        for compute_resource in (self.cr_internal, self.cr_external):
            with self.subTest(compute_resource):
                container = entities.DockerHubContainer(
                    command='date',
                    compute_resource=compute_resource,
                    organization=[self.org],
                ).create()
                self.assertTrue(container.logs()['logs'])

    @tier2
    @run_only_on('sat')
    @stubbed()
    # Return to that case once BZ 1230710 is fixed (with adding
    # DockerRegistryContainer class to Nailgun)
    def test_positive_create_with_external_registry(self):
        """Create a container pulling an image from a custom external
        registry

        @Feature: Docker

        @Assert: The docker container is created and the image is pulled from
        the external registry

        @Status: Manual
        """

    @tier1
    @run_only_on('sat')
    def test_positive_delete(self):
        """Delete containers in local and external compute resources

        @Feature: Docker

        @Assert: The docker containers are deleted in local and external
        compute resources
        """
        for compute_resource in (self.cr_internal, self.cr_external):
            with self.subTest(compute_resource.url):
                container = entities.DockerHubContainer(
                    command='top',
                    compute_resource=compute_resource,
                    organization=[self.org],
                ).create()
                container.delete()
                with self.assertRaises(HTTPError):
                    container.read()


class DockerRegistryTestCase(APITestCase):
    """Tests specific to performing CRUD methods against ``Registries``
    repositories.
    """
    url = DOCKER_0_EXTERNAL_REGISTRY

    @tier1
    @run_only_on('sat')
    def test_positive_create_with_name(self):
        """Create an external docker registry

        @Feature: Docker

        @Assert: External registry is created successfully
        """
        for name in valid_data_list():
            with self.subTest(name):
                description = gen_string('alphanumeric')
                registry = entities.Registry(
                    description=description,
                    name=name,
                    url=self.url,
                ).create()
                try:
                    self.assertEqual(registry.name, name)
                    self.assertEqual(registry.url, self.url)
                    self.assertEqual(registry.description, description)
                finally:
                    registry.delete()

    @tier1
    @run_only_on('sat')
    def test_positive_update_name(self):
        """Create an external docker registry and update its name

        @Feature: Docker

        @Assert: the external registry is updated with the new name
        """
        registry = entities.Registry(
            name=gen_string('alpha'), url=self.url).create()
        try:
            for new_name in valid_data_list():
                with self.subTest(new_name):
                    registry.name = new_name
                    registry = registry.update()
                    self.assertEqual(registry.name, new_name)
        finally:
            registry.delete()

    @tier2
    @run_only_on('sat')
    def test_positive_update_url(self):
        """Create an external docker registry and update its URL

        @Feature: Docker

        @Assert: the external registry is updated with the new URL
        """
        new_url = DOCKER_1_EXTERNAL_REGISTRY
        registry = entities.Registry(url=self.url).create()
        try:
            self.assertEqual(registry.url, self.url)
            registry.url = new_url
            registry = registry.update()
            self.assertEqual(registry.url, new_url)
        finally:
            registry.delete()

    @tier2
    @run_only_on('sat')
    def test_positive_update_description(self):
        """Create an external docker registry and update its description

        @Feature: Docker

        @Assert: the external registry is updated with the new description
        """
        registry = entities.Registry(url=self.url).create()
        try:
            for new_desc in valid_data_list():
                with self.subTest(new_desc):
                    registry.description = new_desc
                    registry = registry.update()
                    self.assertEqual(registry.description, new_desc)
        finally:
            registry.delete()

    @tier2
    @run_only_on('sat')
    def test_positive_update_username(self):
        """Create an external docker registry and update its username

        @Feature: Docker

        @Assert: the external registry is updated with the new username
        """
        username = gen_string('alpha')
        new_username = gen_string('alpha')
        registry = entities.Registry(
            username=username,
            password=gen_string('alpha'),
            url=self.url,
        ).create()
        try:
            self.assertEqual(registry.username, username)
            registry.username = new_username
            registry = registry.update()
            self.assertEqual(registry.username, new_username)
        finally:
            registry.delete()

    @tier1
    @run_only_on('sat')
    def test_positive_delete(self):
        """Create an external docker registry and then delete it

        @Feature: Docker

        @Assert: The external registry is deleted successfully
        """
        registry = entities.Registry(url=self.url).create()
        registry.delete()
        with self.assertRaises(HTTPError):
            registry.read()
