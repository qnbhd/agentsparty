"""Canonical render() strings for the home-page diagrams.

The TypeScript datasets in ``docs/components/diagrams/datasets/index.ts`` embed
these strings verbatim (global protocol lines, endpoint lines, accessible text
versions). This file rebuilds each protocol from the library and asserts that
render() still prints exactly those strings. It is run by
``scripts/check-mdx-examples.py`` in the same pass that checks ``python exec``
blocks, so a rename inside render() fails the docs build instead of silently
diverging from the diagrams.

Add a new diagram here first, then mirror its strings into the dataset.
"""

from agentsparty.kernel.errors import ProjectionError
from agentsparty.kernel.role import roles
from agentsparty.protocol import Text, alt, case, msg, project, project_all, rec, render, var

# ---- DiagThreeRoleSequence: Writer -> Reviewer : Draft, alt, Revise back ----

THREE_ROLE_SEQUENCE = """rec review
  Writer -> Reviewer : Draft(str)
  Reviewer -> Writer {
    Approve():
      Reviewer -> Tools : Publish(str)
      end
    Revise():
      review
  }"""


def three_role_sequence() -> str:
    Writer, Reviewer, Tools = roles('Writer', 'Reviewer', 'Tools')
    return render(
        rec(
            'review',
            msg[Writer, Reviewer](case('Draft', Text))
            >> alt[Reviewer, Writer](
                case('Approve') >> msg[Reviewer, Tools](case('Publish', Text)),
                case('Revise') >> var('review'),
            ),
        ).close()
    )


# ---- DiagProjection: Writer, Reviewer, Archivist; the erasure is the point ----

THREE_ROLE_PROJECTION_GLOBAL = """Writer -> Reviewer : Draft(str)
Reviewer -> Writer : Note(str)
Writer -> Archivist : Final(str)
end"""

THREE_ROLE_PROJECTION_WRITER = """!Reviewer : Draft(str)
?Reviewer : Note(str)
!Archivist : Final(str)
end"""

THREE_ROLE_PROJECTION_REVIEWER = """?Writer : Draft(str)
!Writer : Note(str)
end"""

THREE_ROLE_PROJECTION_ARCHIVIST = """?Writer : Final(str)
end"""


def three_role_projection() -> tuple[str, dict[str, str]]:
    Writer, Reviewer, Archivist = roles('Writer', 'Reviewer', 'Archivist')
    protocol = (
        msg[Writer, Reviewer](case('Draft', Text))
        >> msg[Reviewer, Writer](case('Note', Text))
        >> msg[Writer, Archivist](case('Final', Text))
    ).close()
    views = {role.name: render(endpoint) for role, endpoint in project_all(protocol)}
    return render(protocol), views


# ---- DiagKnowledgeOfChoice: broken vs fixed, and why the fix works ----

BROKEN_GLOBAL = """A -> B {
  No():
    C -> A : N(str)
    end
  Yes():
    A -> C : Y(str)
    end
}"""

FIXED_GLOBAL = """A -> B {
  No():
    A -> C : No(str)
    C -> A : N(str)
    end
  Yes():
    A -> C : Yes(str)
    A -> C : Y(str)
    end
}"""

FIXED_LOCAL_C = """?A {
  No(str):
    !A : N(str)
    end
  Yes(str):
    ?A : Y(str)
    end
}"""

ERROR_MESSAGE = """role 'C' cannot tell the branches of the alt A -> B apart:
  on 'No' it must send N to A (as C), on 'Yes' it must receive Y from A (as C).
A role that behaves differently per branch must be told which branch was taken — add a message from A (or B) to C inside each branch."""


def knowledge_of_alt() -> tuple[str, str, str, str]:
    A, B, C = roles('A', 'B', 'C')
    broken = alt[A, B](
        case('Yes') >> msg[A, C]('Y', Text),
        case('No') >> msg[C, A]('N', Text),
    ).close()
    fixed = alt[A, B](
        case('Yes') >> msg[A, C]('Yes', Text) >> msg[A, C]('Y', Text),
        case('No') >> msg[A, C]('No', Text) >> msg[C, A]('N', Text),
    ).close()
    try:
        project(broken, C)
    except ProjectionError as err:
        error = str(err)
    else:
        raise AssertionError('project(broken, C) should have raised ProjectionError')
    return render(broken), error, render(fixed), render(project(fixed, C))


def main() -> None:
    assert three_role_sequence() == THREE_ROLE_SEQUENCE, 'DiagThreeRoleSequence diverged'

    global_text, views = three_role_projection()
    assert global_text == THREE_ROLE_PROJECTION_GLOBAL, 'DiagProjection global diverged'
    assert views['Writer'] == THREE_ROLE_PROJECTION_WRITER, 'DiagProjection Writer diverged'
    assert views['Reviewer'] == THREE_ROLE_PROJECTION_REVIEWER, 'DiagProjection Reviewer diverged'
    assert views['Archivist'] == THREE_ROLE_PROJECTION_ARCHIVIST, 'DiagProjection Archivist diverged'

    broken_global, error, fixed_global, fixed_local = knowledge_of_alt()
    assert broken_global == BROKEN_GLOBAL, 'DiagKnowledgeOfChoice broken global diverged'
    assert error == ERROR_MESSAGE, 'DiagKnowledgeOfChoice error message diverged'
    assert fixed_global == FIXED_GLOBAL, 'DiagKnowledgeOfChoice fixed global diverged'
    assert fixed_local == FIXED_LOCAL_C, 'DiagKnowledgeOfChoice fixed local view diverged'


if __name__ == '__main__':
    main()
