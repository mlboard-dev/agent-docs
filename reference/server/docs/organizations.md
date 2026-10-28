> 来源：[server/docs/organizations.md](https://github.com/mlboard-dev/server/blob/15f9b7577ce00934246e1e0b7ae219809b1b1590/docs/organizations.md) · `15f9b75`。链接已整理；勘误及示例泛化见[来源说明](../../../SOURCES.md)。部署行为以目标实例的 capabilities / registry / schemas 为准。

# Organizations and project administration

MLBoard has three administrative levels. An instance administrator manages users and instance settings. Organization access always requires explicit organization membership, including for instance administrators. An organization owner/admin, or an instance administrator who has joined that organization, manages its members and project authorization directory. A project owner/admin manages only that project's experiments and collaboration.

Any active signed-in account can create an organization and becomes its owner in the same transaction. API keys cannot create or manage organizations. Organization lists contain only the caller's memberships. Knowing another organization's ID does not grant access to its details, members, settings or project directory; an existing organization manager must add the account first. Instance administrators cannot use their global role to add themselves to an organization they have not joined.

Management does not implicitly grant experiment access. Open an organization's project directory and add an existing organization member to the project as admin, editor or viewer. To read data yourself, grant your own account an explicit project membership. A global API key is always limited by the owner's current project memberships; it does not cross organization boundaries automatically.

Organization members are added by an exact known username or user ID. Organization admins cannot change owners or promote owners. Project admins cannot change project owners or delete projects. Organization owners and instance administrators who belong to the organization can restore project ownership through the same member API. Each organization and project must retain an active owner.

Removing an organization member removes their project memberships, project keys and subscriptions in that organization. Transfer any project for which they are the only active owner first. Existing public shares from a removed member become unavailable through live authorization.

Projects belong to one organization. Project slugs are currently **unique within the instance**, including across organizations. Use the project ID in SDK configuration when possible. Organization/project slugs are not data permissions.

On upgrade, existing projects move to the default organization. Their previous project memberships and roles are preserved exactly; the instance administrator gains organization management but no additional project data access.
