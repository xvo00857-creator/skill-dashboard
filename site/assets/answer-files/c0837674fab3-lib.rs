//! BPFF（Binary Packet File Format）解析器
//!
//! 一种极简的二进制容器格式，大端序：
//!
//! ```text
//! 偏移   长度  字段
//! 0      4     魔数 "BPF1"
//! 4      1     版本 (u8)
//! 5      1     标志 (u8)
//! 6      2     块数量 (u16, 大端序)
//! 8      ...   若干个块：
//!              4 字节 块类型 (ASCII)
//!              4 字节 块数据长度 (u32, 大端序)
//!              N 字节 块数据
//! ```
//!
//! 该解析器接收**不可信二进制输入**（例如来自网络或文件），
//! 是模糊测试的典型目标。

use std::fmt;

pub const MAGIC: &[u8; 4] = b"BPF1";
pub const HEADER_LEN: usize = 8;
pub const CHUNK_HEADER_LEN: usize = 8;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Chunk {
    pub chunk_type: [u8; 4],
    pub data: Vec<u8>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct File {
    pub version: u8,
    pub flags: u8,
    pub chunks: Vec<Chunk>,
}

/// 解析错误。
///
/// 解析器对任何畸形输入都**应当**返回 `Err`，而不是 panic。
#[derive(Debug, PartialEq, Eq)]
pub enum ParseError {
    /// 输入长度不足以承载所声明的结构。
    TooShort,
    /// 魔数不匹配。
    BadMagic,
}

impl fmt::Display for ParseError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            ParseError::TooShort => f.write_str("input too short for declared structure"),
            ParseError::BadMagic => f.write_str("bad magic bytes"),
        }
    }
}

impl std::error::Error for ParseError {}

/// 解析一段不可信的 BPFF 二进制数据。
///
/// # 安全性
///
/// 入参 `data` 可来自任意不可信来源。函数对任何畸形输入都应返回
/// `Err(ParseError)`，不得 panic。
pub fn parse(data: &[u8]) -> Result<File, ParseError> {
    // 文件头至少 8 字节
    if data.len() < HEADER_LEN {
        return Err(ParseError::TooShort);
    }
    if data[0..4] != *MAGIC {
        return Err(ParseError::BadMagic);
    }
    let version = data[4];
    let flags = data[5];
    let num_chunks = u16::from_be_bytes([data[6], data[7]]);

    let mut chunks = Vec::with_capacity(num_chunks as usize);
    let mut offset = HEADER_LEN;

    for _ in 0..num_chunks {
        // 块头 8 字节
        if offset + CHUNK_HEADER_LEN > data.len() {
            return Err(ParseError::TooShort);
        }
        let chunk_type = [data[offset], data[offset + 1], data[offset + 2], data[offset + 3]];
        let chunk_len = u32::from_be_bytes([
            data[offset + 4],
            data[offset + 5],
            data[offset + 6],
            data[offset + 7],
        ]) as usize;
        offset += CHUNK_HEADER_LEN;

        // === 已知缺陷（待 fuzz 发现并修复）===
        // 此处直接使用 data[offset..offset + chunk_len]，
        // 既没有校验 offset + chunk_len <= data.len()，
        // 也没有处理 offset + chunk_len 的整数溢出。
        // 当块声明的数据长度大于实际剩余字节时，会触发切片越界 panic。
        let chunk_data = data[offset..offset + chunk_len].to_vec();
        offset += chunk_len;

        chunks.push(Chunk {
            chunk_type,
            data: chunk_data,
        });
    }

    Ok(File {
        version,
        flags,
        chunks,
    })
}

/// 构造一个合法的 BPFF 文件字节流（用于种子语料和测试）。
pub fn build_file(version: u8, flags: u8, chunks: &[([u8; 4], &[u8])]) -> Vec<u8> {
    let mut out = Vec::new();
    out.extend_from_slice(MAGIC);
    out.push(version);
    out.push(flags);
    out.extend_from_slice(&(chunks.len() as u16).to_be_bytes());
    for (ct, cd) in chunks {
        out.extend_from_slice(ct);
        out.extend_from_slice(&(cd.len() as u32).to_be_bytes());
        out.extend_from_slice(cd);
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_valid_file() {
        let input = build_file(1, 0, &[(*b"DATA", b"hello"), (*b"META", b"42")]);
        let f = parse(&input).expect("valid file should parse");
        assert_eq!(f.version, 1);
        assert_eq!(f.chunks.len(), 2);
        assert_eq!(&f.chunks[0].data, b"hello");
        assert_eq!(&f.chunks[1].data, b"42");
    }

    #[test]
    fn rejects_bad_magic() {
        let mut input = build_file(1, 0, &[]);
        input[0] = b'X';
        assert_eq!(parse(&input), Err(ParseError::BadMagic));
    }

    #[test]
    fn rejects_short_header() {
        assert_eq!(parse(b"BPF"), Err(ParseError::TooShort));
    }
}
