#!/usr/bin/env node
// 演示用修复副本（非 Skill 原文件）。
// 原文件 version-bump-skill/version-bump/scripts/generate_changelog.js 存在语法错误：
//   1) 单引号字符串内含真实换行（第8-9行、第24-26行）
//   2) 模板字符串以反引号开头却以单引号结尾（第28-29行）
// 本副本仅将这些字符串改为合法的转义写法，逻辑未变，用于验证脚本预期行为。
const fs = require('fs');

function generate() {
  try {
    const input = fs.readFileSync(0, 'utf8');
    if (!input || input.trim() === '') {
      process.stderr.write('No input received on stdin\n');
      process.exit(1);
    }

    const releases = JSON.parse(input);
    const lines = ['# Changelog', '', 'All notable changes to this project.', ''];

    releases.slice(0, 50).forEach(r => {
      const date = r.published_at.split('T')[0];
      lines.push(`## [${r.tag_name}] - ${date}`);
      lines.push('');
      if (r.body) lines.push(r.body.trim());
      lines.push('');
    });

    process.stdout.write(lines.join('\n') + '\n');
  } catch (err) {
    process.stderr.write(`Error generating changelog: ${err.message}\n`);
    process.exit(1);
  }
}

generate();
