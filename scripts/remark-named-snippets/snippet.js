const fs = require('fs')
const glob = require('glob')
const htmlparser2 = require('htmlparser2')

/**
 * Constructs a map associating names with snippets by parsing source code.
 *
 * @param {string} dir - The directory of source code to traverse when constructing the map.
 * @returns {object} The "snippet map", which is an object with name, snippet key-value pairs.
 */
function constructSnippetMap (dir) {
  const snippets = parseDirectory(dir)

  const snippetMap = {}
  for (const snippet of snippets) {
    const name = snippet.name
    if (name in snippetMap) {
      throw new Error(
        `A snippet named ${name} has already been defined elsewhere`
      )
    }
    snippetMap[name] = snippet
  }

  return snippetMap
}

/**
 * Parses an input directory using an HTML parser to collect snippets.
 *
 * @param {string} dir - The directory to parse for snippet definitions.
 * @returns {object[]} A list of snippet objects parsed from the input directory.
 */
function parseDirectory (dir) {
  const files = glob.sync(dir + '/**/*.py')

  const allSnippets = []
  for (const file of files) {
    const snippets = parseFile(file)
    for (const snippet of snippets) {
      allSnippets.push(snippet)
    }
  }

  return allSnippets
}

/**
 * Parses an input file using an HTML parser to collect user-defined snippets.
 *
 * @param {string} file - The file to parse for snippet definitions.
 * @returns {object[]} A list of snippet objects parsed from the input file.
 */
function parseFile (file) {
  const data = fs.readFileSync(file, 'utf8')

  // The stack here is used to deal with nested snippets.
  // Everytime we see an open tag, we create a new snippet on the stack.
  const stack = []

  // Once the top snippet on the stack recieves an end tag, we pop it from the stack
  // and add it to our result snippets.
  let snippets = []

  const parser = new htmlparser2.Parser({
    onopentag (tagname, attrs) {
      if (tagname !== 'snippet') {
        return
      }

      const snippetName = attrs.name
      stack.push({ name: snippetName, file: file, contents: '' })
    },
    ontext (text) {
      if (stack.length === 0) {
        return
      }
      text = sanitizeText(text)

      // If we have nested snippets, all snippets on the stack need to be updated
      // to reflect any nested content
      for (let i = 0; i < stack.length; i++) {
        stack[i].contents += text
      }
    },
    onclosetag (tagname) {
      if (tagname !== 'snippet') {
        return
      }

      if (stack.length === 0) {
        throw new Error(`Closing tag found before any opening tags in ${file}`)
      }

      const popped = stack.pop()
      snippets.push(popped)
    }
  })
  parser.write(data)
  parser.end()

  snippets = snippets.filter((s) => s.name)

  const length = snippets.length
  if (length) {
    console.log(`Collected ${length} reference(s) from ${file}`)
  }
  return snippets
}

/**
 * Strips any unnecessary whitespace and source code comments from the ends of the input string.
 * Additionally, removes any nested snippet tags (as applicable).
 *
 * @param {string} text - The text to be sanitized.
 * @returns {string} The sanitized string.
 */
function sanitizeText (text) {
  // Remove leading carriage return
  if (text.startsWith('\n') || text.startsWith('\r')) {
    text = text.substring(1, text.length)
  }

  // Determine indentation
  let indent = "";
  for (let i = 0; i < text.length; i++) {
    if (text[i] === " ") {
      indent += " ";
    } else {
      break;
    }
  }

  // Remove any Python comment remnants
  text = text.trim()
  if (text.endsWith('#')) {
    text = text.substring(0, text.length - 1)
  }

  // Uniformly remove indentation across snippet
  function unindent(line) {
    if (line.startsWith(indent)) {
      line = line.substring(indent.length, text.length)
    }
    return line
  }

  return text
    .split('\n')
    .map(unindent)
    .filter((l) => !(l.includes('<snippet') || l.includes('snippet>')))
    .join('\n')
    .trim()
}

module.exports = constructSnippetMap
