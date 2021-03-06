/*
 SMPS writer tests.

 Copyright (C) 2013 AMPL Optimization Inc

 Permission to use, copy, modify, and distribute this software and its
 documentation for any purpose and without fee is hereby granted,
 provided that the above copyright notice appear in all copies and that
 both that the copyright notice and this permission notice and warranty
 disclaimer appear in supporting documentation.

 The author and AMPL Optimization Inc disclaim all warranties with
 regard to this software, including all implied warranties of
 merchantability and fitness.  In no event shall the author be liable
 for any special, indirect or consequential damages or any damages
 whatsoever resulting from loss of use, data or profits, whether in an
 action of contract, negligence or other tortious action, arising out
 of or in connection with the use or performance of this software.

 Author: Victor Zverovich
 */

#include "gtest/gtest.h"

#include "smpswriter/smpswriter.h"
#include "../util.h"

namespace {

::testing::AssertionResult AssertFilesEqual(const char *, const char *,
    const std::string &expected_file, const std::string &actual_file) {
  auto expected = Split(ReadFile(expected_file), '\n');
  auto actual = Split(ReadFile(actual_file), '\n');
  if (expected.size() > actual.size())
    actual.resize(expected.size());
  else if (actual.size() > expected.size())
    expected.resize(actual.size());
  for (std::size_t i = 0,
      n = std::min(expected.size(), actual.size()); i != n; ++i) {
    if (expected[i] != actual[i]) {
      return ::testing::AssertionFailure()
        << "Files differ in line " << i + 1 << "\n"
        << "Expected file: " << expected_file << "\n"
        << "Actual file: " << actual_file << "\n"
        << "Expected line: " << expected[i] << "\n"
        << "Actual line: " << actual[i] << "\n";
    }
  }
  return ::testing::AssertionSuccess();
}

#define EXPECT_FILES_EQ(expected_file, actual_file) \
    EXPECT_PRED_FORMAT2(AssertFilesEqual, expected_file, actual_file)

void Solve(const char *stub) {
  mp::SMPSWriter writer;
  mp::ColProblem problem(writer, stub);
  mp::SMPSWriter::NLProblemBuilder adapter(problem);
  mp::ReadNLFile(std::string(stub) + ".nl", adapter);
  mp::NullSolutionHandler sol_handler;
  writer.Solve(problem, sol_handler);
}

void CopyFileIfExists(fmt::CStringRef src, fmt::CStringRef dst) {
  FILE *f = std::fopen(src.c_str(), "r");
  if (!f) return;
  std::fclose(f);
  WriteFile(dst, ReadFile(src));
}

class TempSMPSFiles {
 private:
  std::string path_;

 public:
  explicit TempSMPSFiles(std::string path)
    : path_(std::string(MP_TEST_DATA_DIR) + "/" + path) {
    WriteFile("test.nl", ReadFile(path_ + ".nl"));
    CopyFileIfExists(path_ + ".col", "test.col");
    CopyFileIfExists(path_ + ".row", "test.row");
  }

  ~TempSMPSFiles() {
    std::remove("test.col");
    std::remove("test.row");
  }

  const std::string &path() const { return path_; }
};

TEST(SMPSWriterTest, SMPSOutput) {
  static const char *const EXTS[] = {".cor", ".sto", ".tim"};
  static std::string PROBLEMS[] = {
      "int-var", "random-bound", "random-con-matrix", "random-con-matrix2",
      "random-rhs", "single-scenario", "single-stage",
      "vars-not-in-stage-order", "zero-core-coefs", "zero-core-con"
  };
  int count = 0;
  for (size_t i = 0, n = sizeof(PROBLEMS) / sizeof(*PROBLEMS); i != n; ++i) {
    TempSMPSFiles files("smps/" + PROBLEMS[i]);
    Solve("test");
    for (size_t j = 0, n = sizeof(EXTS) / sizeof(*EXTS); j != n; ++j, ++count)
      EXPECT_FILES_EQ(files.path() + EXTS[j], std::string("test") + EXTS[j]);
  }
  EXPECT_EQ(10 * 3, count);
}

TEST(SMPSWriterTest, NonlinearNotSupported) {
  WriteFile("test.nl", ReadFile(MP_TEST_DATA_DIR "/smps/nonlinear.nl"));
  EXPECT_THROW(Solve("test"), mp::Error);
}

TEST(SMPSWriterTest, MoreThan2StagesNotSupported) {
  WriteFile("test.nl", ReadFile(MP_TEST_DATA_DIR "/smps/three-stage.nl"));
  EXPECT_THROW(Solve("test"), mp::Error);
}

TEST(SMPSWriterTest, RangesNotSupported) {
  TempSMPSFiles files("smps/range-con");
  EXPECT_THROW(Solve("test"), mp::Error);
}

TEST(SMPSWriterTest, InconsistentProbabilities) {
  std::string filename = MP_TEST_DATA_DIR "/smps/inconsistent-probabilities";
  WriteFile("test.nl", ReadFile(filename + ".nl"));
  WriteFile("test.row", ReadFile(filename + ".row"));
  WriteFile("test.col", ReadFile(filename + ".col"));
  EXPECT_THROW(Solve("test"), mp::Error);
}
}
